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
        gt=0,
        le=2100,
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


class ArchivoInfo(BaseModel):
    nombre_original: str
    supabase_url: str

    def get_nombre_original(self) -> str:
        return self.nombre_original

    def set_nombre_original(self, valor: str) -> None:
        self.nombre_original = valor

    def get_supabase_url(self) -> str:
        return self.supabase_url

    def set_supabase_url(self, valor: str) -> None:
        self.supabase_url = valor


class DocumentoExtraccion(BaseModel):
    fecha_procesamiento: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    archivo: ArchivoInfo
    extraccion_qwen: PlanoHistorico

    def get_fecha_procesamiento(self) -> datetime:
        return self.fecha_procesamiento

    def set_fecha_procesamiento(self, valor: datetime) -> None:
        self.fecha_procesamiento = valor

    def get_archivo(self) -> ArchivoInfo:
        return self.archivo

    def set_archivo(self, valor: ArchivoInfo) -> None:
        self.archivo = valor

    def get_extraccion_qwen(self) -> PlanoHistorico:
        return self.extraccion_qwen

    def set_extraccion_qwen(self, valor: PlanoHistorico) -> None:
        self.extraccion_qwen = valor


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
        self._task_id = task_id
        self._status = status
        self._filename = filename
        self._created_at = created_at or datetime.utcnow().isoformat()
        self._updated_at = updated_at or datetime.utcnow().isoformat()
        self._resultado = resultado
        self._error = error
        self._supabase_url = supabase_url

    def get_task_id(self) -> str:
        return self._task_id

    def set_task_id(self, valor: str) -> None:
        self._task_id = valor

    def get_status(self) -> TaskStatus:
        return self._status

    def set_status(self, valor: TaskStatus) -> None:
        self._status = valor

    def get_filename(self) -> Optional[str]:
        return self._filename

    def set_filename(self, valor: Optional[str]) -> None:
        self._filename = valor

    def get_created_at(self) -> str:
        return self._created_at

    def set_created_at(self, valor: str) -> None:
        self._created_at = valor

    def get_updated_at(self) -> str:
        return self._updated_at

    def set_updated_at(self, valor: str) -> None:
        self._updated_at = valor

    def get_resultado(self) -> Optional[Dict[str, Any]]:
        return self._resultado

    def set_resultado(self, valor: Optional[Dict[str, Any]]) -> None:
        self._resultado = valor

    def get_error(self) -> Optional[str]:
        return self._error

    def set_error(self, valor: Optional[str]) -> None:
        self._error = valor

    def get_supabase_url(self) -> Optional[str]:
        return self._supabase_url

    def set_supabase_url(self, valor: Optional[str]) -> None:
        self._supabase_url = valor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.get_task_id(),
            "status": self.get_status().value,
            "filename": self.get_filename(),
            "created_at": self.get_created_at(),
            "updated_at": self.get_updated_at(),
            "resultado": self.get_resultado(),
            "error": self.get_error(),
            "supabase_url": self.get_supabase_url(),
        }

