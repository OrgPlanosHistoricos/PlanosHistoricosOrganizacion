"""Modelos relacionales del catálogo de planos y conexión a PostgreSQL con SQLModel."""
from datetime import datetime, timezone
from enum import Enum
import os
from typing import List, Optional

from pydantic import field_validator
from sqlalchemy import DateTime, Index, text
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine


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
    """Metadatos leídos del plano: mismos campos que PlanoHistorico."""

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
    circunscripcion: str = ""
    seccion: str = ""
    manzana: str = ""
    parcela_catastral: str = ""
    nomenclatura: Optional[str] = None
    estado: EstadoPlano = EstadoPlano.pendiente
    ia_estado: EstadoIA = EstadoIA.procesando
    ia_error: Optional[str] = None
    ia_propuesta: Optional[str] = None
    creado_por: Optional[str] = None
    validado_por: Optional[str] = None


class Plano(PlanoBase, table=True):
    __tablename__ = "planos"
    __table_args__ = (Index("ux_planos_nomenclatura", "nomenclatura", unique=True),)

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


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://planos:planos@localhost:5432/planos_db")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_timeout=5,
    connect_args={"connect_timeout": 3} if DATABASE_URL.startswith("postgresql") else {},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS texto_extraido TEXT;"))
        # Los registros anteriores quedan sin nomenclatura hasta su revisión.
        for campo in ("circunscripcion", "seccion", "manzana", "parcela_catastral"):
            conn.execute(text(f"ALTER TABLE planos ADD COLUMN IF NOT EXISTS {campo} TEXT NOT NULL DEFAULT '';"))
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS nomenclatura TEXT;"))
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS creado_por TEXT;"))
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS validado_por TEXT;"))
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS ia_propuesta TEXT;"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_planos_nomenclatura ON planos (nomenclatura);"))
        conn.commit()


def get_session():
    with Session(engine) as session:
        yield session

