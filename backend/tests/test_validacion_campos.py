import unittest

from pydantic import ValidationError
from src.planos.schemas import PlanoValidar, PlanoModificar
from src.tareas.schemas import PlanoHistorico


class ValidacionCamposTests(unittest.TestCase):
    def entrada(self, esquema, **campos):
        return esquema(circunscripcion='3', seccion='K', manzana='12', parcela_catastral='5', motivo='Corrección', **campos)

    def test_anios_invalidos(self):
        for esquema in (PlanoValidar, PlanoModificar):
            for anio in (-1930, 0, 1930.5, 'chino', 2500):
                with self.subTest(esquema=esquema.__name__, anio=anio):
                    with self.assertRaises(ValidationError):
                        self.entrada(esquema, anio=anio)
        with self.assertRaises(ValidationError):
            PlanoHistorico(anio=-1)

    def test_anios_validos_y_vacios(self):
        for esquema in (PlanoValidar, PlanoModificar):
            self.assertEqual(self.entrada(esquema, anio=1930).anio, 1930)
            self.assertIsNone(self.entrada(esquema, anio='').anio)
            self.assertIsNone(self.entrada(esquema).anio)

    def test_escalas(self):
        for esquema in (PlanoValidar, PlanoModificar):
            for vacio in (None, '', '   ', 'null', ' NULL '):
                self.assertIsNone(self.entrada(esquema, escala=vacio).escala)
            for escala in ('CHINO', '0:100', '1:0', '-1:100', '1:100 basura'):
                with self.subTest(escala=escala):
                    with self.assertRaises(ValidationError):
                        self.entrada(esquema, escala=escala)
            for escala in ('1:100', '2:1', '1:2,5', 'Sin escala', 'Escalas varias', ''):
                self.entrada(esquema, escala=escala)
