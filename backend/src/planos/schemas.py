"""Esquemas de entrada y salida del recurso /planos."""
from datetime import datetime
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, Field
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

    def get_id(self) -> int:
        return self.id

    def set_id(self, valor: int) -> None:
        self.id = valor

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

    def get_usuario_id(self) -> str:
        return self.usuario_id

    def set_usuario_id(self, valor: str) -> None:
        self.usuario_id = valor

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

    def get_id(self) -> int:
        return self.id

    def set_id(self, valor: int) -> None:
        self.id = valor

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


class PlanoRead(PlanoBase):
    id: int
    id_inmueble: Optional[int] = None
    creado_en: datetime
    actualizado_en: datetime

    def get_id(self) -> int:
        return self.id

    def set_id(self, valor: int) -> None:
        self.id = valor

    def get_id_inmueble(self) -> Optional[int]:
        return self.id_inmueble

    def set_id_inmueble(self, valor: Optional[int]) -> None:
        self.id_inmueble = valor

    def get_creado_en(self) -> datetime:
        return self.creado_en

    def set_creado_en(self, valor: datetime) -> None:
        self.creado_en = valor

    def get_actualizado_en(self) -> datetime:
        return self.actualizado_en

    def set_actualizado_en(self, valor: datetime) -> None:
        self.actualizado_en = valor


class PlanoDetalle(PlanoRead):
    eventos: List[EventoRead] = []
    procesamientos: List[ProcesamientoRead] = []

    def get_eventos(self) -> List[EventoRead]:
        return self.eventos

    def set_eventos(self, valor: List[EventoRead]) -> None:
        self.eventos = valor

    def get_procesamientos(self) -> List[ProcesamientoRead]:
        return self.procesamientos

    def set_procesamientos(self, valor: List[ProcesamientoRead]) -> None:
        self.procesamientos = valor


class NomenclaturaEntrada(SQLModel):
    circunscripcion: str
    seccion: str
    manzana: str
    parcela_catastral: str

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


class PlanoValidar(DatosPlano, NomenclaturaEntrada):
    parcela: str = ""
    usuario_id: str = "anonimo"

    def get_parcela(self) -> str:
        return self.parcela

    def set_parcela(self, valor: str) -> None:
        self.parcela = valor

    def get_usuario_id(self) -> str:
        return self.usuario_id

    def set_usuario_id(self, valor: str) -> None:
        self.usuario_id = valor


class PlanoModificar(DatosPlano, NomenclaturaEntrada):
    parcela: str = ""
    motivo: str
    usuario_id: str = "anonimo"

    def get_parcela(self) -> str:
        return self.parcela

    def set_parcela(self, valor: str) -> None:
        self.parcela = valor

    def get_motivo(self) -> str:
        return self.motivo

    def set_motivo(self, valor: str) -> None:
        self.motivo = valor

    def get_usuario_id(self) -> str:
        return self.usuario_id

    def set_usuario_id(self, valor: str) -> None:
        self.usuario_id = valor


# Datos que la IA extrae de la imagen de un plano
class PlanoHistorico(BaseModel):
    texto_extraido: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("texto_extraido", "texto extraido"),
        description=(
            "Transcripción completa de TODO el texto legible que se encuentre en el plano "
            "(carátula, recuadros, rótulos, firmas, sellos, notas, cotas, leyendas, etc.). "
            "Extraé primero aquí absolutamente todo el texto antes de clasificarlo en los demás campos."
        ),
    )
    arquitecto: Optional[str] = Field(
        None,
        description=(
            "Nombre completo de quien proyectó o firmó el plano como autor "
            "(arquitecto o proyectista). Suele aparecer junto a rótulos como "
            "'Arq.', 'Arquitecto', 'Proyectó', 'Proyecto' o 'Autor', o como firma. "
            "Solo el nombre, sin el título ni el rótulo. Null si no hay un autor identificable."
        ),
    )
    anio: Optional[int] = Field(
        None,
        description=(
            "Año del plano o del proyecto, como número de 4 dígitos (ej. 1936). "
            "Si figuran varias fechas (proyecto, aprobación, reforma), usar la del "
            "proyecto o dibujo; las demás pueden mencionarse en 'notas' con su leyenda."
        ),
    )
    titulo: Optional[str] = Field(
        None,
        description=(
            "Título o rótulo del plano, normalmente en la cartela o rótulo del plano. "
            "Suele ser un nombre de edificio, obra o proyecto, o una descripción de la vista "
            "(ej. 'Planta baja', 'Fachada principal', 'Corte longitudinal'). Null si no hay título."
        ),
    )
    ubicacion: Optional[str] = Field(
        None, description="Ciudad, dirección o ubicación mencionada en el plano"
    )
    escala: Optional[str] = Field(
        None, description="Escala del plano, ej. '1:100'"
    )
    tipo_de_plano: Optional[str] = Field(
        None, description="Tipo de plano: planta, corte, fachada, detalle, etc."
    )
    material_soporte: Optional[str] = Field(
        None,
        description=(
            "Material del soporte SOLO si está indicado por escrito en el plano "
            "(papel, tela, calco, etc.). No lo deduzcas de cómo se ve la imagen."
        ),
    )
    notas: Optional[str] = Field(
        None,
        description=(
            "Último recurso. Texto relevante que NO encaja en ningún otro campo: "
            "leyendas, aclaraciones, sellos institucionales, números de expediente. "
            "No incluir nombres de personas ni datos que ya estén en otro campo. "
            "Null si no hay nada."
        ),
    )

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

    class Config:
        json_schema_extra = {
            "example": {
                "texto_extraido": "MUNICIPALIDAD DE AZUL\nPALACIO MUNICIPAL\nPROYECTO: ARQ. FRANCISCO SALAMONE\nAÑO: 1936\nESCALA 1:50\nFACHADA PRINCIPAL\nSello del archivo municipal",
                "arquitecto": "Francisco Salamone",
                "anio": 1936,
                "titulo": "Palacio Municipal de Azul",
                "ubicacion": "Azul, Buenos Aires",
                "escala": "1:50",
                "tipo_de_plano": "fachada principal",
                "material_soporte": "papel tela",
                "notas": "Sello del archivo municipal en la esquina inferior derecha",
            }
        }
