"""
Worker en segundo plano que corre la IA sobre los planos creados con POST /planos
y guarda el resultado en la fila correspondiente de Postgres.
"""
import asyncio
import logging
from typing import Optional

from sqlmodel import Session, select

from .database import engine
from .minio_client import existe_archivo, obtener_archivo, obtener_preview_key
from .models import DatosPlano, EstadoIA, EstadoPlano, Plano, ahora
from .preprocessing import pdf_page_to_jpeg_bytes, preprocess_image
from .vision_client import ExtraccionError, extraer_datos_plano

logger = logging.getLogger("planos.worker")


def _extraer(image_bytes: bytes, usar_gpu: bool = False) -> tuple[dict, bool]:
    """
    Intenta extraer datos del plano.
    Si se solicitó GPU y falla (por ejemplo por VRAM insuficiente o falta de driver),
    hace fallback automático reintentando con CPU.
    Devuelve (datos_dict, usado_gpu_real).
    """
    ultimo_error = None
    if usar_gpu:
        try:
            logger.info("Intentando extracción con GPU...")
            for _ in range(2):
                try:
                    return extraer_datos_plano(image_bytes, usar_gpu=True).model_dump(), True
                except ExtraccionError as exc:
                    ultimo_error = exc
            logger.warning(f"Extracción con GPU falló ({ultimo_error}). Aplicando fallback automático a CPU...")
        except Exception as exc:
            logger.warning(f"Error inesperado usando GPU ({exc}). Aplicando fallback automático a CPU...")

    # Extracción por CPU (por defecto o fallback)
    for _ in range(2):
        try:
            return extraer_datos_plano(image_bytes, usar_gpu=False).model_dump(), False
        except ExtraccionError as exc:
            ultimo_error = exc

    raise ExtraccionError(f"No se pudo extraer la información del plano: {ultimo_error}")


def _guardar_resultado(plano_id: int, datos: Optional[dict], error: Optional[str], usado_gpu: bool = False, tipo_gpu: str = "CPU") -> None:
    with Session(engine) as session:
        plano = session.get(Plano, plano_id)
        if plano is None:
            return
        plano.usado_gpu = usado_gpu
        plano.tipo_gpu = tipo_gpu if usado_gpu else "CPU"
        if datos is None:
            plano.ia_estado = EstadoIA.error
            plano.ia_error = error
        else:
            # Si una persona ya validó el plano mientras la IA corría, sus datos mandan
            if plano.estado == EstadoPlano.pendiente:
                for campo in DatosPlano.model_fields:
                    setattr(plano, campo, datos.get(campo))
            plano.ia_estado = EstadoIA.completado
            plano.ia_error = None
        plano.actualizado_en = ahora()
        session.add(plano)
        session.commit()


def _planos_sin_terminar() -> list[tuple[int, bytes, bool, str]]:
    with Session(engine) as session:
        planos = session.exec(select(Plano).where(Plano.ia_estado == EstadoIA.procesando)).all()
        resultado = []
        for p in planos:
            try:
                if p.content_type == "application/pdf":
                    preview_key = obtener_preview_key(p.minio_path)
                    if existe_archivo(preview_key):
                        bytes_img = obtener_archivo(preview_key)
                    else:
                        pdf_bytes = obtener_archivo(p.minio_path)
                        bytes_img = pdf_page_to_jpeg_bytes(pdf_bytes, page_index=0)
                else:
                    bytes_img = obtener_archivo(p.minio_path)
                resultado.append((p.id, bytes_img, bool(p.usado_gpu), getattr(p, "tipo_gpu", "CPU") or "CPU"))
            except Exception as exc:
                logger.error(f"No se pudo recuperar archivo del plano pendiente {p.id}: {exc}")
        return resultado


class PlanosWorker:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def encolar(self, plano_id: int, image_bytes: bytes, usar_gpu: bool = False, tipo_gpu: str = "CPU") -> None:
        self.queue.put_nowait((plano_id, image_bytes, usar_gpu, tipo_gpu))

    async def _loop(self) -> None:
        # La cola vive en memoria: lo que quedó a medias antes de un reinicio se retoma acá
        try:
            for plano_id, image_bytes, usar_gpu, tipo_gpu in await asyncio.to_thread(_planos_sin_terminar):
                self.encolar(plano_id, image_bytes, usar_gpu, tipo_gpu)
        except Exception:
            logger.exception("No se pudieron recuperar los planos pendientes de IA")

        while True:
            plano_id, image_bytes, usar_gpu, tipo_gpu = await self.queue.get()
            try:
                await self._procesar(plano_id, image_bytes, usar_gpu, tipo_gpu)
            except Exception:
                logger.exception(f"Error guardando el resultado de IA del plano {plano_id}")
            finally:
                self.queue.task_done()

    async def _procesar(self, plano_id: int, image_bytes: bytes, usar_gpu: bool = False, tipo_gpu: str = "CPU") -> None:
        logger.info(f"Procesando IA del plano {plano_id} (usar_gpu={usar_gpu}, tipo_gpu={tipo_gpu})...")
        try:
            datos, usado_gpu_real = await asyncio.to_thread(_extraer, image_bytes, usar_gpu)
        except Exception as exc:
            logger.warning(f"IA falló para el plano {plano_id}: {exc}")
            await asyncio.to_thread(_guardar_resultado, plano_id, None, str(exc), False, "CPU")
            return
        tipo_final = tipo_gpu if usado_gpu_real else "CPU"
        await asyncio.to_thread(_guardar_resultado, plano_id, datos, None, usado_gpu_real, tipo_final)
        logger.info(f"IA completada para el plano {plano_id} (modo={tipo_final}).")


planos_worker = PlanosWorker()
