"""
Gestor de tareas en segundo plano para el procesamiento asíncrono de planos con IA.
Permite encolar trabajos, ejecutarlos en un hilo separado sin bloquear el bucle de
eventos de FastAPI, y consultar el estado y resultado mediante un ID de tarea.
"""
import asyncio
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Dict, Optional
import uuid

from .db_client import coleccion_extracciones
from .preprocessing import preprocess_image
from .schemas import ArchivoInfo, DocumentoExtraccion, PlanoHistorico
from .storage_client import subir_plano
from .vision_client import ExtraccionError, extraer_datos_plano

logger = logging.getLogger("planos.tasks")
logging.basicConfig(level=logging.INFO)


def _guardar_extraccion(
    filename: str, content_type: str, image_bytes: bytes, resultado: PlanoHistorico
) -> str:
    """Sube el archivo original a Supabase e inserta el documento final en MongoDB.

    Devuelve la URL pública del archivo subido.
    """
    supabase_url = subir_plano(image_bytes, filename, content_type)
    documento = DocumentoExtraccion(
        archivo=ArchivoInfo(nombre_original=filename, supabase_url=supabase_url),
        extraccion_qwen=resultado,
    )
    coleccion_extracciones.insert_one(documento.model_dump())
    return supabase_url


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


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, TareaInfo] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    def start_worker(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Worker de tareas de IA iniciado en segundo plano.")

    async def stop_worker(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Worker de tareas de IA detenido.")

    def crear_tarea(self, filename: str, content_type: str, image_bytes: bytes) -> TareaInfo:
        task_id = str(uuid.uuid4())
        tarea = TareaInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            filename=filename,
        )
        self.tasks[task_id] = tarea

        # Evitar crecimiento desmedido de memoria reteniendo las últimas 500 tareas
        if len(self.tasks) > 500:
            oldest_key = next(iter(self.tasks))
            self.tasks.pop(oldest_key, None)

        self.queue.put_nowait((task_id, image_bytes, content_type))
        logger.info(f"Tarea encolada: {task_id} ({filename})")
        return tarea

    def obtener_tarea(self, task_id: str) -> Optional[TareaInfo]:
        return self.tasks.get(task_id)

    def listar_tareas(self) -> list[TareaInfo]:
        return list(reversed(list(self.tasks.values())))

    async def _worker_loop(self):
        while True:
            try:
                task_id, image_bytes, content_type = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                await self._procesar_tarea(task_id, image_bytes, content_type)
            except Exception as exc:
                logger.error(
                    f"Error crítico en worker al procesar tarea {task_id}: {exc}",
                    exc_info=True,
                )
            finally:
                self.queue.task_done()

    async def _procesar_tarea(self, task_id: str, image_bytes: bytes, content_type: str):
        tarea = self.tasks.get(task_id)
        if not tarea:
            return

        tarea.status = TaskStatus.PROCESSING
        tarea.updated_at = datetime.utcnow().isoformat()
        logger.info(f"Iniciando procesamiento IA para tarea {task_id}...")

        try:
            # 1. Preprocesamiento de imagen en thread separado
            imagen_procesada = await asyncio.to_thread(preprocess_image, image_bytes, content_type)

            # 2. Inferencia con Ollama (con reintento) en thread separado
            ultimo_error = None
            resultado: Optional[PlanoHistorico] = None
            for intento in range(2):
                try:
                    resultado = await asyncio.to_thread(
                        extraer_datos_plano, imagen_procesada
                    )
                    break
                except ExtraccionError as exc:
                    ultimo_error = exc
                    logger.warning(
                        f"Intento {intento + 1} fallido para tarea {task_id}: {exc}"
                    )
                    if intento == 0:
                        await asyncio.sleep(1)

            if resultado is None:
                raise ExtraccionError(
                    f"No se pudo extraer la información del plano: {ultimo_error}"
                )

            # 3. Subida a Supabase Storage + insert en MongoDB, en thread separado
            supabase_url = await asyncio.to_thread(
                _guardar_extraccion, tarea.filename, content_type, image_bytes, resultado
            )

            tarea.status = TaskStatus.COMPLETED
            tarea.resultado = resultado.model_dump()
            tarea.supabase_url = supabase_url
            tarea.updated_at = datetime.utcnow().isoformat()
            logger.info(f"Tarea {task_id} finalizada exitosamente.")

        except Exception as exc:
            tarea.status = TaskStatus.ERROR
            tarea.error = str(exc)
            tarea.updated_at = datetime.utcnow().isoformat()
            logger.error(f"Tarea {task_id} finalizada con error: {exc}")
        finally:
            del image_bytes


task_manager = TaskManager()


async def procesar_directo(
    image_bytes: bytes, filename: str, content_type: str
) -> PlanoHistorico:
    """Procesamiento directo síncrono para llamadas con ?sync=true sin bloquear el event loop."""
    imagen_procesada = await asyncio.to_thread(preprocess_image, image_bytes, content_type)
    ultimo_error = None
    for intento in range(2):
        try:
            resultado = await asyncio.to_thread(extraer_datos_plano, imagen_procesada)
            await asyncio.to_thread(
                _guardar_extraccion, filename, content_type, image_bytes, resultado
            )
            return resultado
        except ExtraccionError as exc:
            ultimo_error = exc
            if intento == 0:
                await asyncio.sleep(1)
    raise ExtraccionError(
        f"No se pudo extraer la información del plano: {ultimo_error}"
    )

