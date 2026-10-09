"""Modelos relacionales del catálogo de planos (tablas + esquemas de request/response)."""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import field_validator
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class EstadoPlano(str, Enum):
    pendiente = "pendiente"
    validado = "validado"
    sin_ubicacion = "sin_ubicacion"


class EstadoIA(str, Enum):
    procesando = "procesando"
    completado = "completado"
    error = "error"
    no_aplica = "no_aplica"


class DatosPlano(SQLModel):
    """Metadatos leídos del plano: mismos campos que PlanoHistorico (api/schemas.py)."""

    texto_extraido: Optional[str] = None
    arquitecto: Optional[str] = None
    anio: Optional[int] = None
    titulo: Optional[str] = None
    ubicacion: Optional[str] = None
    escala: Optional[str] = None
    tipo_de_plano: Optional[str] = None
    material_soporte: Optional[str] = None
    notas: Optional[str] = None

    # Los inputs vacíos de un formulario llegan como "" y no son un año válido
    @field_validator("anio", mode="before")
    @classmethod
    def _anio_vacio_es_null(cls, valor):
        return None if valor == "" else valor


class PlanoBase(DatosPlano):
    nombre_original: str
    content_type: str
    ubicacion_fisica: str = ""
    expediente: str = ""
    direccion_referencia: str = ""
    parcela: str = ""
    estado: EstadoPlano = EstadoPlano.pendiente
    ia_estado: EstadoIA = EstadoIA.procesando
    ia_error: Optional[str] = None
    creado_por: Optional[str] = None
    validado_por: Optional[str] = None


class Plano(PlanoBase, table=True):
    __tablename__ = "planos"

    id: Optional[int] = Field(default=None, primary_key=True)
    minio_path: str
    creado_en: datetime = Field(default_factory=ahora, sa_type=DateTime(timezone=True))
    actualizado_en: datetime = Field(default_factory=ahora, sa_type=DateTime(timezone=True))

    eventos: List["EventoAuditoria"] = Relationship(
        back_populates="plano",
        sa_relationship_kwargs={"order_by": "EventoAuditoria.fecha"},
    )
    procesamientos: List["ProcesamientoIA"] = Relationship(
        back_populates="plano",
        sa_relationship_kwargs={"order_by": "ProcesamientoIA.fecha"},
    )


class EventoAuditoria(SQLModel, table=True):
    __tablename__ = "eventos_auditoria"

    id: Optional[int] = Field(default=None, primary_key=True)
    plano_id: int = Field(foreign_key="planos.id", index=True)
    usuario_id: str
    fecha: datetime = Field(default_factory=ahora, sa_type=DateTime(timezone=True))
    motivo: str

    plano: Optional[Plano] = Relationship(back_populates="eventos")


class ProcesamientoIA(SQLModel, table=True):
    __tablename__ = "procesamientos_ia"

    id: Optional[int] = Field(default=None, primary_key=True)
    plano_id: int = Field(foreign_key="planos.id", index=True)
    intento: int
    estado: EstadoIA
    error: Optional[str] = None
    fecha: datetime = Field(default_factory=ahora, sa_type=DateTime(timezone=True))

    plano: Optional[Plano] = Relationship(back_populates="procesamientos")


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


class PlanoValidar(DatosPlano):
    parcela: str = ""
    usuario_id: str = "anonimo"


class PlanoModificar(DatosPlano):
    parcela: str = ""
    motivo: str
    usuario_id: str = "anonimo"
