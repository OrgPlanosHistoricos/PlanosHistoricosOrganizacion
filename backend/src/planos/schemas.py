"""Esquemas de entrada y salida del recurso /planos."""
from datetime import datetime
from typing import List, Optional

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
    circunscripcion: str
    seccion: str
    manzana: str
    parcela_catastral: str


class PlanoValidar(DatosPlano, NomenclaturaEntrada):
    parcela: str = ""
    usuario_id: str = "anonimo"


class PlanoModificar(DatosPlano, NomenclaturaEntrada):
    parcela: str = ""
    motivo: str
    usuario_id: str = "anonimo"

