import asyncio
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from src.compartido.sesion import get_session
from src.errors import ExtraccionError
from src.models import EstadoIA, EventoAuditoria, Plano, ProcesamientoIA
from src.planos import worker as planos_worker_mod
from src.planos.nomenclatura import clave_nomenclatura, normalizar_nomenclatura
from src.planos.routes import router
from src.planos.worker import _guardar_resultado
from src.tareas.schemas import PlanoHistorico


class NomenclaturaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        SQLModel.metadata.create_all(self.engine)
        app = FastAPI()
        app.include_router(router)

        def session():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_session] = session
        self.client = TestClient(app)
        self.upload = patch("src.planos.services.subir_archivo", return_value="test/archivo.jpg")
        self.queue = patch("src.planos.services.planos_worker.encolar")
        self.upload_mock = self.upload.start()
        self.queue_mock = self.queue.start()
        self.addCleanup(self.upload.stop)
        self.addCleanup(self.queue.stop)
        self.addCleanup(self.client.close)
        self.addCleanup(self.engine.dispose)
        self.data = dict(circunscripcion="03", seccion=" k ", manzana="012 A", parcela_catastral="05 b")

    def create(self, data=None, headers=None):
        return self.client.post(
            "/planos",
            data=self.data if data is None else data,
            files={"archivo": ("test.jpg", b"test", "image/jpeg")},
            headers=headers or {},
        )

    def test_normalizacion_y_datos_opcionales(self):
        res = self.create(headers={"X-Forwarded-For": "192.168.1.50"})
        self.assertEqual(res.status_code, 201, res.text)
        doc = res.json()
        self.assertEqual(doc["nomenclatura"], "3-K-12A-5B")
        self.assertEqual(doc["expediente"], "")
        self.assertEqual(doc["ubicacion_fisica"], "")
        self.assertEqual(doc["direccion_referencia"], "")
        self.assertEqual(doc["hash_sha256"], hashlib.sha256(b"test").hexdigest())
        self.assertEqual(doc["tamano_bytes"], 4)
        self.assertTrue(doc["activo"])
        self.assertIsNone(doc["validado_en"])
        with Session(self.engine) as db:
            eventos = db.exec(select(EventoAuditoria)).all()
            self.assertEqual(len(eventos), 1)
            self.assertEqual(eventos[0].accion, "Carga")
            self.assertEqual(eventos[0].ip_origen, "192.168.1.50")
            self.assertIsNone(eventos[0].valores_anteriores)
            self.assertEqual(json.loads(eventos[0].valores_nuevos)["nomenclatura"], "3-K-12A-5B")
            procs = db.exec(select(ProcesamientoIA)).all()
            self.assertEqual(len(procs), 1)
            self.assertEqual(procs[0].modelo_ia, "qwen2.5-vl:3b")
            self.assertIsNotNone(procs[0].version_prompt)
            self.assertIsNotNone(procs[0].parametros_preprocesamiento)
        self.queue_mock.assert_called_once()

    def test_faltantes_e_invalidos_no_suben_archivo(self):
        for campo in self.data:
            datos = self.data.copy()
            del datos[campo]
            self.assertEqual(self.create(datos).status_code, 422)
            for valor in ("", "???", "<script>"):
                datos[campo] = valor
                self.assertEqual(self.create(datos).status_code, 422)
        for campo in ("circunscripcion", "manzana", "parcela_catastral"):
            datos = {**self.data, campo: "0"}
            self.assertEqual(self.create(datos).status_code, 422)
        self.upload_mock.assert_not_called()

    def test_duplicado_normalizado_no_sube_otro_archivo(self):
        self.assertEqual(self.create().status_code, 201)
        datos = dict(circunscripcion="3", seccion="K", manzana="12a", parcela_catastral="5B")
        res = self.create(datos)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["detail"]["codigo"], "duplicado")
        self.assertEqual(self.upload_mock.call_count, 1)

    def test_no_permite_subir_mas_de_un_plano_a_analizar_a_la_vez(self):
        res1 = self.create()
        self.assertEqual(res1.status_code, 201)
        # Intentar subir otro plano distinto mientras el primero sigue con ia_estado == 'procesando'
        res2 = self.create({**self.data, "manzana": "15"})
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.json()["detail"]["codigo"], "procesando_ia")
        self.assertEqual(self.upload_mock.call_count, 1)

    def test_busqueda_exacta_no_busca_expediente(self):
        self.create({**self.data, "expediente": "EXP-123"})
        res = self.client.get("/planos", params={"q": "03-k-012a-05b"})
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(self.client.get("/planos", params={"q": "3-K-12-5"}).json(), [])
        self.assertEqual(self.client.get("/planos", params={"q": "EXP-123"}).status_code, 422)

    def test_validar_modificar_y_duplicados(self):
        first = self.create().json()["id"]
        with Session(self.engine) as db:
            plano1 = db.get(Plano, first)
            plano1.ia_estado = EstadoIA.completado
            db.add(plano1)
            db.commit()
        second = self.create({**self.data, "manzana": "15"}).json()["id"]
        res_val = self.client.put(f"/planos/{first}/validar", json=self.data)
        self.assertEqual(res_val.status_code, 200)
        self.assertIsNotNone(res_val.json()["validado_en"])
        res = self.client.put(f"/planos/{second}/validar", json=self.data)
        self.assertEqual(res.status_code, 409)
        res = self.client.put(
            f"/planos/{first}/modificar", json={**self.data, "manzana": "15", "motivo": "Corrección"}
        )
        self.assertEqual(res.status_code, 409)
        res = self.client.put(
            f"/planos/{first}/modificar", json={**self.data, "manzana": "20", "motivo": "Corrección"}
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["nomenclatura"], "3-K-20-5B")
        self.assertEqual(res.json()["estado"], "validado")
        eventos = res.json()["eventos"]
        self.assertEqual([e["accion"] for e in eventos], ["Carga", "Validación", "Modificación"])
        self.assertEqual(json.loads(eventos[-1]["valores_anteriores"])["manzana"], "12A")
        self.assertEqual(json.loads(eventos[-1]["valores_nuevos"])["manzana"], "20")

    def test_catalogacion_conserva_texto_original_omitido_o_alterado(self):
        plano_id = self.create().json()["id"]
        original = "Transcripción original\ncon saltos de línea."
        with Session(self.engine) as db:
            plano = db.get(Plano, plano_id)
            plano.texto_extraido = original
            db.add(plano)
            db.commit()
        res = self.client.put(f"/planos/{plano_id}/validar", json=self.data)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["texto_extraido"], original)
        res = self.client.put(
            f"/planos/{plano_id}/modificar",
            json={
                **self.data,
                "motivo": "Corrección de título",
                "titulo": "Título corregido",
                "texto_extraido": "Texto alterado",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["texto_extraido"], original)
        self.assertEqual(res.json()["titulo"], "Título corregido")

    def test_registros_anteriores_se_conservan_y_se_completan(self):
        with Session(self.engine) as db:
            viejo = Plano(
                nombre_original="viejo.pdf", content_type="application/pdf", minio_path="test/viejo"
            )
            db.add(viejo)
            db.commit()
            db.refresh(viejo)
            plano_id = viejo.id
        self.assertIsNone(self.client.get(f"/planos/{plano_id}").json()["nomenclatura"])
        self.assertEqual(self.client.put(f"/planos/{plano_id}/validar", json={}).status_code, 422)
        res = self.client.put(f"/planos/{plano_id}/validar", json=self.data)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["nomenclatura"], "3-K-12A-5B")

    def test_indice_impide_duplicados_en_base_de_datos(self):
        self.create()
        with Session(self.engine) as db:
            db.add(
                Plano(
                    nombre_original="otro.jpg",
                    content_type="image/jpeg",
                    minio_path="otro",
                    nomenclatura="3-K-12A-5B",
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_eliminar_hace_baja_logica_conserva_trazabilidad_y_libera_nomenclatura(self):
        plano_id = self.create().json()["id"]
        res = self.client.delete(f"/planos/{plano_id}")
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(self.client.get(f"/planos/{plano_id}").status_code, 404)
        self.assertEqual(self.client.get("/planos").json(), [])
        with Session(self.engine) as db:
            plano_db = db.get(Plano, plano_id)
            self.assertIsNotNone(plano_db)
            self.assertFalse(plano_db.activo)
            self.assertIsNone(plano_db.nomenclatura)
            eventos = db.exec(select(EventoAuditoria).where(EventoAuditoria.plano_id == plano_id)).all()
            self.assertEqual([e.accion for e in eventos], ["Carga", "Caducidad"])
            self.assertTrue(json.loads(eventos[-1].valores_anteriores)["activo"])
            self.assertFalse(json.loads(eventos[-1].valores_nuevos)["activo"])
            self.assertEqual(len(db.exec(select(ProcesamientoIA)).all()), 1)
        self.assertEqual(self.create().status_code, 201)

    def test_eliminar_ausente_devuelve_404(self):
        self.assertEqual(self.client.delete("/planos/999").status_code, 404)

    def test_worker_actualiza_procesamiento_ia_con_raw_y_metricas(self):
        plano_id = self.create().json()["id"]
        datos_ia = {
            "texto_extraido": "TEXTO CRUDO DEL PLANO",
            "arquitecto": "Salamone",
            "anio": 1937,
            "titulo": "Palacio Municipal",
            "ubicacion": "Azul",
            "escala": "1:100",
            "tipo_de_plano": "planta",
            "material_soporte": "tela",
            "notas": "Exp 1",
        }
        with patch("src.planos.worker.engine", self.engine):
            _guardar_resultado(
                plano_id=plano_id,
                datos=datos_ia,
                error=None,
                duracion_ms=1450,
                modelo_ia="qwen2.5vl:7b",
            )
        detalle = self.client.get(f"/planos/{plano_id}").json()
        self.assertEqual(detalle["texto_extraido"], "TEXTO CRUDO DEL PLANO")
        self.assertEqual(len(detalle["procesamientos"]), 1)
        proc = detalle["procesamientos"][0]
        self.assertEqual(proc["estado"], EstadoIA.completado.value)
        self.assertEqual(proc["modelo_ia"], "qwen2.5vl:7b")
        self.assertEqual(proc["duracion_ms"], 1450)
        self.assertEqual(proc["texto_extraido_raw"], "TEXTO CRUDO DEL PLANO")
        self.assertEqual(json.loads(proc["respuesta_json_raw"])["arquitecto"], "Salamone")
        self.assertIsNotNone(proc["version_prompt"])
        self.assertIsNotNone(proc["parametros_preprocesamiento"])

    def test_reintentar_ia_limite_3_intentos(self):
        with patch("src.planos.services.obtener_archivo", return_value=b"fake-image"):
            plano_id = self.create().json()["id"]
            # El plano recién creado ya tiene intento 1
            with Session(self.engine) as db:
                plano = db.get(Plano, plano_id)
                plano.ia_estado = plano.ia_estado.completado
                db.add(plano)
                db.commit()

            # Reintento 1 (segundo intento total)
            res1 = self.client.post(f"/planos/{plano_id}/reintentar_ia?usuario_id=Operador")
            self.assertEqual(res1.status_code, 200)

            with Session(self.engine) as db:
                plano = db.get(Plano, plano_id)
                plano.ia_estado = plano.ia_estado.completado
                db.add(plano)
                db.commit()

            # Reintento 2 (tercer intento total)
            res2 = self.client.post(f"/planos/{plano_id}/reintentar_ia?usuario_id=Operador")
            self.assertEqual(res2.status_code, 200)

            with Session(self.engine) as db:
                plano = db.get(Plano, plano_id)
                plano.ia_estado = plano.ia_estado.completado
                db.add(plano)
                db.commit()

            # Reintento 3 (cuarto intento total) -> Debe fallar por límite alcanzado
            res3 = self.client.post(f"/planos/{plano_id}/reintentar_ia?usuario_id=Operador")
            self.assertEqual(res3.status_code, 400)
            self.assertEqual(res3.json()["detail"]["codigo"], "max_intentos")

    def test_ia_propuesta_en_modificar_y_descartar(self):
        plano_id = self.create().json()["id"]
        self.assertEqual(self.client.put(f"/planos/{plano_id}/validar", json=self.data).status_code, 200)

        # Simular propuesta guardada
        with Session(self.engine) as db:
            plano = db.get(Plano, plano_id)
            plano.ia_propuesta = '{"titulo": "Propuesta IA"}'
            db.add(plano)
            db.commit()

        # Descartar propuesta
        res_desc = self.client.post(f"/planos/{plano_id}/descartar_propuesta")
        self.assertEqual(res_desc.status_code, 200)
        self.assertIsNone(res_desc.json().get("ia_propuesta"))

        # Modificar plano también debe limpiar ia_propuesta
        with Session(self.engine) as db:
            plano = db.get(Plano, plano_id)
            plano.ia_propuesta = '{"titulo": "Otra propuesta"}'
            db.add(plano)
            db.commit()

        res_mod = self.client.put(
            f"/planos/{plano_id}/modificar", json={**self.data, "motivo": "Ajuste manual"}
        )
        self.assertEqual(res_mod.status_code, 200)
        self.assertIsNone(res_mod.json().get("ia_propuesta"))

    def test_worker_guarda_corrida_ia_en_mongo_exitosa_y_fallida(self):
        plano_id = self.create().json()["id"]
        mock_coleccion = MagicMock()
        resultado_fake = PlanoHistorico(
            texto_extraido="OBRA MUNICIPAL 1938",
            arquitecto="Salamone",
            anio=1938,
            titulo="Palacio",
        )

        with patch.object(planos_worker_mod, "engine", self.engine), \
             patch.object(planos_worker_mod.db_client, "coleccion_corridas_ia", mock_coleccion), \
             patch.object(planos_worker_mod, "extraer_datos_plano", return_value=resultado_fake):
            asyncio.run(planos_worker_mod.planos_worker._procesar(plano_id, b"img"))

        self.assertEqual(mock_coleccion.insert_one.call_count, 1)
        doc_exito = mock_coleccion.insert_one.call_args[0][0]
        self.assertEqual(doc_exito["plano_id"], plano_id)
        self.assertEqual(doc_exito["archivo_id"], "test/archivo.jpg")
        self.assertEqual(doc_exito["version_prompt"], "1.0")
        self.assertEqual(doc_exito["texto_original"], "OBRA MUNICIPAL 1938")
        self.assertIn("OBRA MUNICIPAL 1938", doc_exito["json_crudo"])
        self.assertIsInstance(doc_exito["duracion_segundos"], float)
        self.assertIsNotNone(doc_exito["fecha"])
        self.assertEqual(doc_exito["estado"], "completado")

        # Corrida fallida también se registra en corridas_ia
        mock_coleccion.reset_mock()
        with patch.object(planos_worker_mod, "engine", self.engine), \
             patch.object(planos_worker_mod.db_client, "coleccion_corridas_ia", mock_coleccion), \
             patch.object(planos_worker_mod, "extraer_datos_plano", side_effect=ExtraccionError("fallo IA")):
            asyncio.run(planos_worker_mod.planos_worker._procesar(plano_id, b"img"))

        self.assertEqual(mock_coleccion.insert_one.call_count, 1)
        doc_error = mock_coleccion.insert_one.call_args[0][0]
        self.assertEqual(doc_error["plano_id"], plano_id)
        self.assertEqual(doc_error["archivo_id"], "test/archivo.jpg")
        self.assertEqual(doc_error["estado"], "error")
        self.assertIn("fallo IA", doc_error["error"])


if __name__ == "__main__":
    unittest.main()
