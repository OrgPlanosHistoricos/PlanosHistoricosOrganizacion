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

    def get_texto_extraido(self) -> Optional[str]:
        return self.texto_extraido

    def set_texto_extraido(self, valor: Optional[str]) -> None:
        self.texto_extraido = valor

    def get_arquitecto(self) -> Optional[str]:
        return self.arquitecto

    def set_arquitecto(self, valor: Optional[str]) -> None:
        self.arquitecto = valor

    def get_anio(self) -> Optional[int]:
        return self.anio

    def set_anio(self, valor: Optional[int]) -> None:
        self.anio = valor

    def get_titulo(self) -> Optional[str]:
        return self.titulo

    def set_titulo(self, valor: Optional[str]) -> None:
        self.titulo = valor

    def get_ubicacion(self) -> Optional[str]:
        return self.ubicacion

    def set_ubicacion(self, valor: Optional[str]) -> None:
        self.ubicacion = valor

    def get_escala(self) -> Optional[str]:
        return self.escala

    def set_escala(self, valor: Optional[str]) -> None:
        self.escala = valor

    def get_tipo_de_plano(self) -> Optional[str]:
        return self.tipo_de_plano

    def set_tipo_de_plano(self, valor: Optional[str]) -> None:
        self.tipo_de_plano = valor

    def get_material_soporte(self) -> Optional[str]:
        return self.material_soporte

    def set_material_soporte(self, valor: Optional[str]) -> None:
        self.material_soporte = valor

    def get_notas(self) -> Optional[str]:
        return self.notas

    def set_notas(self, valor: Optional[str]) -> None:
        self.notas = valor


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

    def get_nombre_original(self) -> str:
        return self.nombre_original

    def set_nombre_original(self, valor: str) -> None:
        self.nombre_original = valor

    def get_content_type(self) -> str:
        return self.content_type

    def set_content_type(self, valor: str) -> None:
        self.content_type = valor

    def get_hash_sha256(self) -> Optional[str]:
        return self.hash_sha256

    def set_hash_sha256(self, valor: Optional[str]) -> None:
        self.hash_sha256 = valor

    def get_tamano_bytes(self) -> Optional[int]:
        return self.tamano_bytes

    def set_tamano_bytes(self, valor: Optional[int]) -> None:
        self.tamano_bytes = valor

    def get_ubicacion_fisica(self) -> str:
        return self.ubicacion_fisica

    def set_ubicacion_fisica(self, valor: str) -> None:
        self.ubicacion_fisica = valor

    def get_expediente(self) -> str:
        return self.expediente

    def set_expediente(self, valor: str) -> None:
        self.expediente = valor

    def get_direccion_referencia(self) -> str:
        return self.direccion_referencia

    def set_direccion_referencia(self, valor: str) -> None:
        self.direccion_referencia = valor

    def get_parcela(self) -> str:
        return self.parcela

    def set_parcela(self, valor: str) -> None:
        self.parcela = valor

    def get_circunscripcion(self) -> str:
        return self.circunscripcion

    def set_circunscripcion(self, valor: str) -> None:
        self.circunscripcion = valor

    def get_seccion(self) -> str:
        return self.seccion

    def set_seccion(self, valor: str) -> None:
        self.seccion = valor

    def get_manzana(self) -> str:
        return self.manzana

    def set_manzana(self, valor: str) -> None:
        self.manzana = valor

    def get_parcela_catastral(self) -> str:
        return self.parcela_catastral

    def set_parcela_catastral(self, valor: str) -> None:
        self.parcela_catastral = valor

    def get_nomenclatura(self) -> Optional[str]:
        return self.nomenclatura

    def set_nomenclatura(self, valor: Optional[str]) -> None:
        self.nomenclatura = valor

    def get_estado(self) -> EstadoPlano:
        return self.estado

    def set_estado(self, valor: EstadoPlano) -> None:
        self.estado = valor

    def get_ia_estado(self) -> EstadoIA:
        return self.ia_estado

    def set_ia_estado(self, valor: EstadoIA) -> None:
        self.ia_estado = valor

    def get_ia_error(self) -> Optional[str]:
        return self.ia_error

    def set_ia_error(self, valor: Optional[str]) -> None:
        self.ia_error = valor

    def get_ia_propuesta(self) -> Optional[str]:
        return self.ia_propuesta

    def set_ia_propuesta(self, valor: Optional[str]) -> None:
        self.ia_propuesta = valor

    def get_creado_por(self) -> Optional[str]:
        return self.creado_por

    def set_creado_por(self, valor: Optional[str]) -> None:
        self.creado_por = valor

    def get_validado_por(self) -> Optional[str]:
        return self.validado_por

    def set_validado_por(self, valor: Optional[str]) -> None:
        self.validado_por = valor

    def get_validado_en(self) -> Optional[datetime]:
        return self.validado_en

    def set_validado_en(self, valor: Optional[datetime]) -> None:
        self.validado_en = valor

    def get_activo(self) -> bool:
        return self.activo

    def set_activo(self, valor: bool) -> None:
        self.activo = valor


class Localidad(SQLModel, table=True):
    """Solo lectura: catálogo de localidades de tramitación."""

    __tablename__ = "localidades"
    __table_args__ = {"schema": ESQUEMA_TRAMITACION}

    id_localidad: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    codigo: str
    activo: bool = True

    def get_id_localidad(self) -> Optional[int]:
        return self.id_localidad

    def set_id_localidad(self, valor: Optional[int]) -> None:
        self.id_localidad = valor

    def get_nombre(self) -> str:
        return self.nombre

    def set_nombre(self, valor: str) -> None:
        self.nombre = valor

    def get_codigo(self) -> str:
        return self.codigo

    def set_codigo(self, valor: str) -> None:
        self.codigo = valor

    def get_activo(self) -> bool:
        return self.activo

    def set_activo(self, valor: bool) -> None:
        self.activo = valor


class Inmueble(SQLModel, table=True):
    """Solo lectura: inmuebles de tramitación, nexo entre planos y expedientes."""

    __tablename__ = "inmuebles"
    __table_args__ = {"schema": ESQUEMA_TRAMITACION}

    id_inmueble: Optional[int] = Field(default=None, primary_key=True)
    nomenclatura_catastral: str
    id_localidad: int = Field(foreign_key=f"{ESQUEMA_TRAMITACION}.localidades.id_localidad")
    activo: bool = True

    def get_id_inmueble(self) -> Optional[int]:
        return self.id_inmueble

    def set_id_inmueble(self, valor: Optional[int]) -> None:
        self.id_inmueble = valor

    def get_nomenclatura_catastral(self) -> str:
        return self.nomenclatura_catastral

    def set_nomenclatura_catastral(self, valor: str) -> None:
        self.nomenclatura_catastral = valor

    def get_id_localidad(self) -> int:
        return self.id_localidad

    def set_id_localidad(self, valor: int) -> None:
        self.id_localidad = valor

    def get_activo(self) -> bool:
        return self.activo

    def set_activo(self, valor: bool) -> None:
        self.activo = valor


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

    def get_id(self) -> Optional[int]:
        return self.id

    def set_id(self, valor: Optional[int]) -> None:
        self.id = valor

    def get_id_inmueble(self) -> Optional[int]:
        return self.id_inmueble

    def set_id_inmueble(self, valor: Optional[int]) -> None:
        self.id_inmueble = valor

    def get_minio_path(self) -> str:
        return self.minio_path

    def set_minio_path(self, valor: str) -> None:
        self.minio_path = valor

    def get_creado_en(self) -> datetime:
        return self.creado_en

    def set_creado_en(self, valor: datetime) -> None:
        self.creado_en = valor

    def get_actualizado_en(self) -> datetime:
        return self.actualizado_en

    def set_actualizado_en(self, valor: datetime) -> None:
        self.actualizado_en = valor

    def get_eventos(self) -> List["EventoAuditoria"]:
        return self.eventos

    def set_eventos(self, valor: List["EventoAuditoria"]) -> None:
        self.eventos = valor

    def get_procesamientos(self) -> List["ProcesamientoIA"]:
        return self.procesamientos

    def set_procesamientos(self, valor: List["ProcesamientoIA"]) -> None:
        self.procesamientos = valor


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

    def get_id(self) -> Optional[int]:
        return self.id

    def set_id(self, valor: Optional[int]) -> None:
        self.id = valor

    def get_plano_id(self) -> int:
        return self.plano_id

    def set_plano_id(self, valor: int) -> None:
        self.plano_id = valor

    def get_usuario_id(self) -> str:
        return self.usuario_id

    def set_usuario_id(self, valor: str) -> None:
        self.usuario_id = valor

    def get_fecha(self) -> datetime:
        return self.fecha

    def set_fecha(self, valor: datetime) -> None:
        self.fecha = valor

    def get_accion(self) -> str:
        return self.accion

    def set_accion(self, valor: str) -> None:
        self.accion = valor

    def get_motivo(self) -> str:
        return self.motivo

    def set_motivo(self, valor: str) -> None:
        self.motivo = valor

    def get_valores_anteriores(self) -> Optional[str]:
        return self.valores_anteriores

    def set_valores_anteriores(self, valor: Optional[str]) -> None:
        self.valores_anteriores = valor

    def get_valores_nuevos(self) -> Optional[str]:
        return self.valores_nuevos

    def set_valores_nuevos(self, valor: Optional[str]) -> None:
        self.valores_nuevos = valor

    def get_ip_origen(self) -> Optional[str]:
        return self.ip_origen

    def set_ip_origen(self, valor: Optional[str]) -> None:
        self.ip_origen = valor

    def get_plano(self) -> Optional[Plano]:
        return self.plano

    def set_plano(self, valor: Optional[Plano]) -> None:
        self.plano = valor


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

    def get_id(self) -> Optional[int]:
        return self.id

    def set_id(self, valor: Optional[int]) -> None:
        self.id = valor

    def get_plano_id(self) -> int:
        return self.plano_id

    def set_plano_id(self, valor: int) -> None:
        self.plano_id = valor

    def get_intento(self) -> int:
        return self.intento

    def set_intento(self, valor: int) -> None:
        self.intento = valor

    def get_estado(self) -> EstadoIA:
        return self.estado

    def set_estado(self, valor: EstadoIA) -> None:
        self.estado = valor

    def get_error(self) -> Optional[str]:
        return self.error

    def set_error(self, valor: Optional[str]) -> None:
        self.error = valor

    def get_modelo_ia(self) -> str:
        return self.modelo_ia

    def set_modelo_ia(self, valor: str) -> None:
        self.modelo_ia = valor

    def get_version_prompt(self) -> Optional[str]:
        return self.version_prompt

    def set_version_prompt(self, valor: Optional[str]) -> None:
        self.version_prompt = valor

    def get_parametros_preprocesamiento(self) -> Optional[str]:
        return self.parametros_preprocesamiento

    def set_parametros_preprocesamiento(self, valor: Optional[str]) -> None:
        self.parametros_preprocesamiento = valor

    def get_texto_extraido_raw(self) -> Optional[str]:
        return self.texto_extraido_raw

    def set_texto_extraido_raw(self, valor: Optional[str]) -> None:
        self.texto_extraido_raw = valor

    def get_respuesta_json_raw(self) -> Optional[str]:
        return self.respuesta_json_raw

    def set_respuesta_json_raw(self, valor: Optional[str]) -> None:
        self.respuesta_json_raw = valor

    def get_duracion_ms(self) -> Optional[int]:
        return self.duracion_ms

    def set_duracion_ms(self, valor: Optional[int]) -> None:
        self.duracion_ms = valor

    def get_fecha(self) -> datetime:
        return self.fecha

    def set_fecha(self, valor: datetime) -> None:
        self.fecha = valor

    def get_plano(self) -> Optional[Plano]:
        return self.plano

    def set_plano(self, valor: Optional[Plano]) -> None:
        self.plano = valor


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

