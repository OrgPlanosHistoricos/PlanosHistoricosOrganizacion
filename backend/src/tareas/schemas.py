"""
Esquemas de extracción de planos históricos con IA y estado de tareas asíncronas.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import AliasChoices, BaseModel, Field


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


class ArchivoInfo(BaseModel):
    nombre_original: str
    supabase_url: str


class DocumentoExtraccion(BaseModel):
    fecha_procesamiento: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    archivo: ArchivoInfo
    extraccion_qwen: PlanoHistorico


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class TareaInfo:
    def __init__(
        self,
        task_id: str,
        status: TaskStatus,
        filename: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        resultado: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        supabase_url: Optional[str] = None,
    ):
        self.task_id = task_id
        self.status = status
        self.filename = filename
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.resultado = resultado
        self.error = error
        self.supabase_url = supabase_url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "filename": self.filename,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resultado": self.resultado,
            "error": self.error,
            "supabase_url": self.supabase_url,
        }

