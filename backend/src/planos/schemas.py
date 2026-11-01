"""Esquemas de entrada y salida del recurso /planos."""
from datetime import datetime
from typing import List, Optional
import re

from pydantic import Field, field_validator
from sqlmodel import SQLModel

from src.models import DatosPlano, EstadoIA, PlanoBase


class EventoRead(SQLModel):
    id: int
    fecha: datetime
    accion: str = "Modificación"
    motivo: str
    usuario_id: str
    valores_anteriores: Optional[str] = None
    valores_nuevos: Optional[str] = None
    ip_origen: Optional[str] = None


class ProcesamientoRead(SQLModel):
    id: int
    intento: int
    estado: EstadoIA
    error: Optional[str] = None
    modelo_ia: str = "qwen2.5-vl:3b"
    version_prompt: Optional[str] = None
    parametros_preprocesamiento: Optional[str] = None
    texto_extraido_raw: Optional[str] = None
    respuesta_json_raw: Optional[str] = None
    duracion_ms: Optional[int] = None
    fecha: datetime


class PlanoRead(PlanoBase):
    id: int
    creado_en: datetime
    actualizado_en: datetime


class PlanoDetalle(PlanoRead):
    eventos: List[EventoRead] = []
    procesamientos: List[ProcesamientoRead] = []


class NomenclaturaEntrada(SQLModel):
    circunscripcion: str = ""
    seccion: str = ""
    manzana: str = ""
    parcela_catastral: str = ""


class DatosCatalogacion(DatosPlano):
    """Validación de entradas humanas sin restringir lecturas de registros históricos."""

    @field_validator("escala")
    @classmethod
    def validar_escala(cls, valor):
        if valor is None or not valor.strip() or valor.strip().casefold() == "null":
            return None
        valor = valor.strip()
        especiales = {"sin escala": "Sin escala", "escalas varias": "Escalas varias"}
        if valor.casefold() in especiales:
            return especiales[valor.casefold()]
        partes = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)\s*:\s*([0-9]+(?:[.,][0-9]+)?)", valor)
        if not partes or any(float(p.replace(",", ".")) <= 0 for p in partes.groups()):
            raise ValueError("La escala debe tener formato 1:100, o indicar Sin escala o Escalas varias.")
        return ":".join(p.replace(",", ".") for p in partes.groups())


class PlanoValidar(DatosCatalogacion, NomenclaturaEntrada):
    parcela: str = ""
    usuario_id: str = "anonimo"


class PlanoModificar(DatosCatalogacion, NomenclaturaEntrada):
    parcela: str = ""
    motivo: str = Field(max_length=180)
    usuario_id: str = "anonimo"

