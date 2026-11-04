"""Modelos relacionales del catálogo de planos y conexión a PostgreSQL con SQLModel."""
from datetime import datetime, timezone
from enum import Enum
import os
from typing import List, Optional

from pydantic import field_validator
from sqlalchemy import DateTime, Index, String, Text, text
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine


# Nuestras tablas viven en su propio esquema; "tramitacion" es del backend del otro grupo
# y lo crea su script SQL (db/tramitacion), no init_db().
ESQUEMA = "planos"
ESQUEMA_TRAMITACION = "tramitacion"


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

    texto_extraido: Optional[str] = Field(default=None, sa_type=Text)
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
    hash_sha256: Optional[str] = Field(default=None, max_length=64, sa_type=String(64))
    tamano_bytes: Optional[int] = None
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
    validado_en: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    activo: bool = Field(default=True)


class Localidad(SQLModel, table=True):
    """Solo lectura: catálogo de localidades de tramitación."""

    __tablename__ = "localidades"
    __table_args__ = {"schema": ESQUEMA_TRAMITACION}

    id_localidad: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    codigo: str
    activo: bool = True


class Inmueble(SQLModel, table=True):
    """Solo lectura: inmuebles de tramitación, nexo entre planos y expedientes."""

    __tablename__ = "inmuebles"
    __table_args__ = {"schema": ESQUEMA_TRAMITACION}

    id_inmueble: Optional[int] = Field(default=None, primary_key=True)
    nomenclatura_catastral: str
    id_localidad: int = Field(foreign_key=f"{ESQUEMA_TRAMITACION}.localidades.id_localidad")
    activo: bool = True


class Plano(PlanoBase, table=True):
    __tablename__ = "planos"
    __table_args__ = (
        Index("ux_planos_nomenclatura", "nomenclatura", unique=True),
        {"schema": ESQUEMA},
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    id_inmueble: Optional[int] = Field(
        default=None, foreign_key=f"{ESQUEMA_TRAMITACION}.inmuebles.id_inmueble", index=True
    )
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
    __table_args__ = {"schema": ESQUEMA}

    id: Optional[int] = Field(default=None, primary_key=True)
    plano_id: int = Field(foreign_key=f"{ESQUEMA}.planos.id", index=True)
    usuario_id: str
    fecha: datetime = Field(default_factory=ahora, sa_type=DateTime(timezone=True))
    accion: str = Field(default="Modificación", max_length=15, sa_type=String(15))
    motivo: str
    valores_anteriores: Optional[str] = Field(default=None, sa_type=Text)
    valores_nuevos: Optional[str] = Field(default=None, sa_type=Text)
    ip_origen: Optional[str] = Field(default=None, max_length=45, sa_type=String(45))

    plano: Optional[Plano] = Relationship(back_populates="eventos")


class ProcesamientoIA(SQLModel, table=True):
    __tablename__ = "procesamientos_ia"
    __table_args__ = {"schema": ESQUEMA}

    id: Optional[int] = Field(default=None, primary_key=True)
    plano_id: int = Field(foreign_key=f"{ESQUEMA}.planos.id", index=True)
    intento: int
    estado: EstadoIA
    error: Optional[str] = None
    modelo_ia: str = Field(default="qwen2.5-vl:3b", max_length=100, sa_type=String(100))
    version_prompt: Optional[str] = Field(default=None, max_length=30, sa_type=String(30))
    parametros_preprocesamiento: Optional[str] = Field(default=None, sa_type=Text)
    texto_extraido_raw: Optional[str] = Field(default=None, sa_type=Text)
    respuesta_json_raw: Optional[str] = Field(default=None, sa_type=Text)
    duracion_ms: Optional[int] = None
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
    with engine.begin() as conn:
        if conn.execute(text(f"SELECT to_regclass('{ESQUEMA_TRAMITACION}.inmuebles')")).scalar() is None:
            raise RuntimeError(
                f"Falta el esquema '{ESQUEMA_TRAMITACION}': hay que cargar db/tramitacion en Postgres antes de iniciar la API."
            )
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {ESQUEMA};"))
        # Las tablas vivían en public: se mueven con sus datos, secuencias e índices.
        for tabla in ("planos", "eventos_auditoria", "procesamientos_ia"):
            conn.execute(text(f"ALTER TABLE IF EXISTS public.{tabla} SET SCHEMA {ESQUEMA};"))

    # Las tablas de tramitación son del otro grupo: solo creamos las nuestras.
    SQLModel.metadata.create_all(
        engine, tables=[Plano.__table__, EventoAuditoria.__table__, ProcesamientoIA.__table__]
    )
    with engine.connect() as conn:
        # Migraciones de tabla planos
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS texto_extraido TEXT;"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS hash_sha256 VARCHAR(64);"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS tamano_bytes INTEGER;"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS validado_en TIMESTAMPTZ;"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE;"))
        # Los registros anteriores quedan sin nomenclatura hasta su revisión.
        for campo in ("circunscripcion", "seccion", "manzana", "parcela_catastral"):
            conn.execute(text(f"ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS {campo} TEXT NOT NULL DEFAULT '';"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS nomenclatura TEXT;"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS creado_por TEXT;"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS validado_por TEXT;"))
        conn.execute(text("ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS ia_propuesta TEXT;"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_planos_nomenclatura ON planos.planos (nomenclatura);"))
        conn.execute(text(
            "ALTER TABLE planos.planos ADD COLUMN IF NOT EXISTS id_inmueble INTEGER "
            "REFERENCES tramitacion.inmuebles (id_inmueble);"
        ))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_planos_planos_id_inmueble ON planos.planos (id_inmueble);"))

        # Migraciones de tabla eventos_auditoria
        conn.execute(text("ALTER TABLE planos.eventos_auditoria ADD COLUMN IF NOT EXISTS accion VARCHAR(15) NOT NULL DEFAULT 'Modificación';"))
        conn.execute(text("ALTER TABLE planos.eventos_auditoria ADD COLUMN IF NOT EXISTS valores_anteriores TEXT;"))
        conn.execute(text("ALTER TABLE planos.eventos_auditoria ADD COLUMN IF NOT EXISTS valores_nuevos TEXT;"))
        conn.execute(text("ALTER TABLE planos.eventos_auditoria ADD COLUMN IF NOT EXISTS ip_origen VARCHAR(45);"))

        # Migraciones de tabla procesamientos_ia
        conn.execute(text("ALTER TABLE planos.procesamientos_ia ADD COLUMN IF NOT EXISTS modelo_ia VARCHAR(100) NOT NULL DEFAULT 'qwen2.5-vl:3b';"))
        conn.execute(text("ALTER TABLE planos.procesamientos_ia ADD COLUMN IF NOT EXISTS version_prompt VARCHAR(30);"))
        conn.execute(text("ALTER TABLE planos.procesamientos_ia ADD COLUMN IF NOT EXISTS parametros_preprocesamiento TEXT;"))
        conn.execute(text("ALTER TABLE planos.procesamientos_ia ADD COLUMN IF NOT EXISTS texto_extraido_raw TEXT;"))
        conn.execute(text("ALTER TABLE planos.procesamientos_ia ADD COLUMN IF NOT EXISTS respuesta_json_raw TEXT;"))
        conn.execute(text("ALTER TABLE planos.procesamientos_ia ADD COLUMN IF NOT EXISTS duracion_ms INTEGER;"))
        conn.commit()


def get_session():
    with Session(engine) as session:
        yield session

