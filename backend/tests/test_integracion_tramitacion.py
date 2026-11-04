"""Integración con el esquema tramitacion del otro grupo contra el Postgres de DATABASE_URL.

Requiere db/tramitacion cargado. Correr con PRUEBAS_POSTGRES=1, por ejemplo:
    docker compose run --rm -e PRUEBAS_POSTGRES=1 api python -m unittest tests.test_integracion_tramitacion
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.models import engine, init_db
from src.planos.routes import router

NOMENCLATURA = "99-Z-999-999"
EXPEDIENTE = "EXP-LP-2026-999999"


@unittest.skipUnless(os.environ.get("PRUEBAS_POSTGRES") == "1", "requiere Postgres con tramitacion")
class IntegracionTramitacionTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.addCleanup(self._limpiar)
        with engine.begin() as conn:
            self.id_inmueble = conn.execute(text(
                "INSERT INTO tramitacion.inmuebles (nomenclatura_catastral, id_localidad) "
                "SELECT :nomen, id_localidad FROM tramitacion.localidades WHERE codigo = 'LP' "
                "RETURNING id_inmueble"
            ), {"nomen": NOMENCLATURA}).scalar_one()
            conn.execute(text(
                "INSERT INTO tramitacion.expedientes "
                "(numero_expediente, id_profesional_externo, id_solicitante, id_inmueble, id_tipo_obra) "
                "SELECT :num, 'prof-prueba', min(s.id_solicitante), :inm, min(t.id_tipo_obra) "
                "FROM tramitacion.solicitantes s, tramitacion.tipos_obra t"
            ), {"num": EXPEDIENTE, "inm": self.id_inmueble})

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        for objetivo in ("src.planos.services.subir_archivo", "src.planos.services.planos_worker.encolar"):
            parche = patch(objetivo, return_value="test/archivo.jpg")
            parche.start()
            self.addCleanup(parche.stop)

    def _limpiar(self):
        with engine.begin() as conn:
            planos = "SELECT id FROM planos.planos WHERE minio_path = 'test/archivo.jpg'"
            conn.execute(text(f"DELETE FROM planos.eventos_auditoria WHERE plano_id IN ({planos})"))
            conn.execute(text(f"DELETE FROM planos.procesamientos_ia WHERE plano_id IN ({planos})"))
            conn.execute(text("DELETE FROM planos.planos WHERE minio_path = 'test/archivo.jpg'"))
            conn.execute(text("DELETE FROM tramitacion.expedientes WHERE numero_expediente = :num"), {"num": EXPEDIENTE})
            conn.execute(text("DELETE FROM tramitacion.inmuebles WHERE nomenclatura_catastral = :n"), {"n": NOMENCLATURA})

    def test_plano_queda_vinculado_y_se_consulta_desde_ambos_lados(self):
        circ, secc, mza, parc = NOMENCLATURA.split("-")
        res = self.client.post(
            "/planos",
            data=dict(circunscripcion=circ, seccion=secc, manzana=mza, parcela_catastral=parc),
            files={"archivo": ("test.jpg", b"test", "image/jpeg")},
        )
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()["id_inmueble"], self.id_inmueble)
        plano_id = res.json()["id"]

        with engine.connect() as conn:
            # Lado tramitación: planos históricos del inmueble de un expediente
            desde_expediente = conn.execute(text(
                "SELECT p.id FROM planos.planos p "
                "JOIN tramitacion.expedientes e ON e.id_inmueble = p.id_inmueble "
                "WHERE e.numero_expediente = :num AND p.activo"
            ), {"num": EXPEDIENTE}).scalars().all()
            # Lado planos: expedientes del inmueble de un plano
            desde_plano = conn.execute(text(
                "SELECT e.numero_expediente FROM tramitacion.expedientes e "
                "JOIN planos.planos p ON p.id_inmueble = e.id_inmueble WHERE p.id = :id"
            ), {"id": plano_id}).scalars().all()
        self.assertEqual(desde_expediente, [plano_id])
        self.assertEqual(desde_plano, [EXPEDIENTE])

    def test_fk_impide_apuntar_a_un_inmueble_inexistente(self):
        with self.assertRaises(IntegrityError), engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO planos.planos (nombre_original, content_type, minio_path, id_inmueble, "
                "ubicacion_fisica, expediente, direccion_referencia, parcela, circunscripcion, seccion, "
                "manzana, parcela_catastral, estado, ia_estado, activo, creado_en, actualizado_en) "
                "VALUES ('x.jpg', 'image/jpeg', 'test/archivo.jpg', -1, '', '', '', '', '', '', '', '', "
                "'pendiente', 'no_aplica', true, now(), now())"
            ))


if __name__ == "__main__":
    unittest.main()
