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
    id_inmueble: Optional[int] = None
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
