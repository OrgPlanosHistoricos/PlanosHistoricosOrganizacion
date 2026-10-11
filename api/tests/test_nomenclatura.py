import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool

from api.models import Plano, EventoAuditoria, ProcesamientoIA
from api.database import get_session
from api.planos_router import router
from api.nomenclatura import normalizar_nomenclatura, clave_nomenclatura


class NomenclaturaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        SQLModel.metadata.create_all(self.engine)
        app = FastAPI()
        app.include_router(router)
        def session():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_session] = session
        self.client = TestClient(app)
        self.upload = patch('api.planos_router.subir_archivo', return_value='test/archivo.jpg')
        self.queue = patch('api.planos_router.planos_worker.encolar')
        self.upload_mock = self.upload.start()
        self.queue_mock = self.queue.start()
        self.addCleanup(self.upload.stop)
        self.addCleanup(self.queue.stop)
        self.addCleanup(self.client.close)
        self.addCleanup(self.engine.dispose)
        self.data = dict(circunscripcion='03', seccion=' k ', manzana='012 A', parcela_catastral='05 b')

    def create(self, data=None):
        return self.client.post('/planos', data=self.data if data is None else data,
                                files={'archivo': ('test.jpg', b'test', 'image/jpeg')})

    def test_normalizacion_y_datos_opcionales(self):
        res = self.create()
        self.assertEqual(res.status_code, 201, res.text)
        doc = res.json()
        self.assertEqual(doc['nomenclatura'], '3-K-12A-5B')
        self.assertEqual(doc['expediente'], '')
        self.assertEqual(doc['ubicacion_fisica'], '')
        self.assertEqual(doc['direccion_referencia'], '')
        with Session(self.engine) as db:
            self.assertEqual(len(db.exec(select(EventoAuditoria)).all()), 1)
            self.assertEqual(len(db.exec(select(ProcesamientoIA)).all()), 1)
        self.queue_mock.assert_called_once()

    def test_faltantes_e_invalidos_no_suben_archivo(self):
        for campo in self.data:
            datos = self.data.copy()
            del datos[campo]
            self.assertEqual(self.create(datos).status_code, 422)
            for valor in ('', '???', '<script>'):
                datos[campo] = valor
                self.assertEqual(self.create(datos).status_code, 422)
        for campo in ('circunscripcion', 'manzana', 'parcela_catastral'):
            datos = {**self.data, campo: '0'}
            self.assertEqual(self.create(datos).status_code, 422)
        self.upload_mock.assert_not_called()

    def test_duplicado_normalizado_no_sube_otro_archivo(self):
        self.assertEqual(self.create().status_code, 201)
        datos = dict(circunscripcion='3', seccion='K', manzana='12a', parcela_catastral='5B')
        res = self.create(datos)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()['detail']['codigo'], 'duplicado')
        self.assertEqual(self.upload_mock.call_count, 1)

    def test_busqueda_exacta_no_busca_expediente(self):
        self.create({**self.data, 'expediente': 'EXP-123'})
        res = self.client.get('/planos', params={'q': '03-k-012a-05b'})
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(self.client.get('/planos', params={'q': '3-K-12-5'}).json(), [])
        self.assertEqual(self.client.get('/planos', params={'q': 'EXP-123'}).status_code, 422)

    def test_validar_modificar_y_duplicados(self):
        first = self.create().json()['id']
        second = self.create({**self.data, 'manzana': '15'}).json()['id']
        self.assertEqual(self.client.put(f'/planos/{first}/validar', json=self.data).status_code, 200)
        res = self.client.put(f'/planos/{second}/validar', json=self.data)
        self.assertEqual(res.status_code, 409)
        res = self.client.put(f'/planos/{first}/modificar', json={**self.data, 'manzana': '15', 'motivo': 'Corrección'})
        self.assertEqual(res.status_code, 409)
        res = self.client.put(f'/planos/{first}/modificar', json={**self.data, 'manzana': '20', 'motivo': 'Corrección'})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()['nomenclatura'], '3-K-20-5B')
        self.assertEqual(res.json()['estado'], 'validado')

    def test_registros_anteriores_se_conservan_y_se_completan(self):
        with Session(self.engine) as db:
            viejo = Plano(nombre_original='viejo.pdf', content_type='application/pdf', minio_path='test/viejo')
            db.add(viejo)
            db.commit()
            db.refresh(viejo)
            plano_id = viejo.id
        self.assertIsNone(self.client.get(f'/planos/{plano_id}').json()['nomenclatura'])
        self.assertEqual(self.client.put(f'/planos/{plano_id}/validar', json={}).status_code, 422)
        res = self.client.put(f'/planos/{plano_id}/validar', json=self.data)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()['nomenclatura'], '3-K-12A-5B')

    def test_indice_impide_duplicados_en_base_de_datos(self):
        self.create()
        with Session(self.engine) as db:
            db.add(Plano(nombre_original='otro.jpg', content_type='image/jpeg', minio_path='otro', nomenclatura='3-K-12A-5B'))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_eliminar_borra_archivos_relaciones_y_libera_nomenclatura(self):
        plano_id = self.create().json()['id']
        with patch('api.planos_router.eliminar_archivo') as borrar:
            res = self.client.delete(f'/planos/{plano_id}')
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual([c.args[0] for c in borrar.call_args_list],
                         ['test/archivo.jpg.preview.jpg', 'test/archivo.jpg'])
        self.assertEqual(self.client.get(f'/planos/{plano_id}').status_code, 404)
        with Session(self.engine) as db:
            self.assertEqual(db.exec(select(EventoAuditoria)).all(), [])
            self.assertEqual(db.exec(select(ProcesamientoIA)).all(), [])
        self.assertEqual(self.create().status_code, 201)

    def test_eliminar_fallo_storage_conserva_registro(self):
        plano_id = self.create().json()['id']
        with patch('api.planos_router.eliminar_archivo', side_effect=RuntimeError('privado')):
            res = self.client.delete(f'/planos/{plano_id}')
        self.assertEqual(res.status_code, 503)
        self.assertNotIn('privado', res.text)
        self.assertEqual(self.client.get(f'/planos/{plano_id}').status_code, 200)

    def test_eliminar_ausente_no_toca_storage(self):
        with patch('api.planos_router.eliminar_archivo') as borrar:
            self.assertEqual(self.client.delete('/planos/999').status_code, 404)
            borrar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
