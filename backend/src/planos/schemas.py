"""Esquemas de entrada y salida del recurso /planos."""
from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel

from src.models import DatosPlano, EstadoIA, PlanoBase


class EventoRead(SQLModel):
    id: int
    fecha: datetime
    motivo: str
    usuario_id: str


class ProcesamientoRead(SQLModel):
    id: int
    intento: int
    estado: EstadoIA
    error: Optional[str] = None
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

