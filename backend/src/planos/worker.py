"""
Worker en segundo plano que corre la IA sobre los planos creados con POST /planos
y guarda el resultado en la fila correspondiente de Postgres.
"""
import asyncio
import json
import logging
import time
from typing import Optional

from sqlmodel import Session, select

from src.compartido.minio_client import existe_archivo, obtener_archivo, obtener_preview_key
from src.compartido.preprocessing import MAX_CAJETIN_DIMENSION, MAX_DIMENSION, pdf_page_to_jpeg_bytes
from src.compartido.sesion import engine
from src.compartido.vision_client import (
    VERSION_PROMPT_EXTRACCION,
    ExtraccionError,
    extraer_datos_plano,
    obtener_modelo_activo,
)
from src.models import DatosPlano, EstadoIA, EstadoPlano, Plano, ProcesamientoIA, ahora

logger = logging.getLogger("planos.worker")


def _parametros_preprocesamiento_default() -> str:
    return json.dumps(
        {
            "max_dimension_deteccion": MAX_DIMENSION,
            "max_dimension_cajetin": MAX_CAJETIN_DIMENSION,
            "autocontrast_cutoff": 1,
            "sharpness_factor": 1.5,
            "padding_pct": 0.02,
            "rotacion": 0,
        },
        ensure_ascii=False,
    )


def _extraer(image_bytes: bytes) -> dict:
    ultimo_error = None
    # Un reintento: los VLM chicos a veces fallan la primera vez
    for _ in range(2):
        try:
            return extraer_datos_plano(image_bytes).model_dump()
        except ExtraccionError as exc:
            ultimo_error = exc
    raise ExtraccionError(f"No se pudo extraer la información del plano: {ultimo_error}")


def _guardar_resultado(
    plano_id: int,
    datos: Optional[dict],
    error: Optional[str],
    duracion_ms: Optional[int] = None,
    modelo_ia: Optional[str] = None,
) -> None:
    with Session(engine) as session:
        plano = session.get(Plano, plano_id)
        if plano is None:
            return
        if datos is None:
            plano.ia_estado = EstadoIA.error
            plano.ia_error = error
        else:
            if plano.estado != EstadoPlano.pendiente:
                plano.ia_propuesta = json.dumps(datos, ensure_ascii=False)
            else:
                for campo in DatosPlano.model_fields:
                    setattr(plano, campo, datos.get(campo))
            plano.ia_estado = EstadoIA.completado
            plano.ia_error = None
        plano.actualizado_en = ahora()
        session.add(plano)

        # Actualizar el registro de ProcesamientoIA correspondiente al último intento
        proc = session.exec(
            select(ProcesamientoIA)
            .where(ProcesamientoIA.plano_id == plano_id)
            .order_by(ProcesamientoIA.intento.desc(), ProcesamientoIA.id.desc())
        ).first()
        if proc is not None:
            proc.estado = EstadoIA.error if datos is None else EstadoIA.completado
            proc.error = error
            if modelo_ia:
                proc.modelo_ia = modelo_ia
            proc.version_prompt = VERSION_PROMPT_EXTRACCION
            proc.parametros_preprocesamiento = _parametros_preprocesamiento_default()
            if duracion_ms is not None:
                proc.duracion_ms = duracion_ms
            if datos is not None:
                proc.texto_extraido_raw = datos.get("texto_extraido")
                proc.respuesta_json_raw = json.dumps(datos, ensure_ascii=False)
            session.add(proc)

        session.commit()


def _planos_sin_terminar() -> list[tuple[int, bytes]]:
    with Session(engine) as session:
        planos = session.exec(
            select(Plano).where(Plano.ia_estado == EstadoIA.procesando, Plano.activo == True)  # noqa: E712
        ).all()
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
                resultado.append((p.id, bytes_img))
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

    def encolar(self, plano_id: int, image_bytes: bytes) -> None:
        self.queue.put_nowait((plano_id, image_bytes))

    async def _loop(self) -> None:
        # La cola vive en memoria: lo que quedó a medias antes de un reinicio se retoma acá
        try:
            for plano_id, image_bytes in await asyncio.to_thread(_planos_sin_terminar):
                self.encolar(plano_id, image_bytes)
        except Exception:
            logger.exception("No se pudieron recuperar los planos pendientes de IA")

        while True:
            plano_id, image_bytes = await self.queue.get()
            try:
                await self._procesar(plano_id, image_bytes)
            except Exception:
                logger.exception(f"Error guardando el resultado de IA del plano {plano_id}")
            finally:
                self.queue.task_done()

    async def _procesar(self, plano_id: int, image_bytes: bytes) -> None:
        logger.info(f"Procesando IA del plano {plano_id}...")
        t0 = time.perf_counter()
        modelo_ia = await asyncio.to_thread(obtener_modelo_activo)
        try:
            datos = await asyncio.to_thread(_extraer, image_bytes)
        except Exception as exc:
            duracion_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning(f"IA falló para el plano {plano_id}: {exc}")
            await asyncio.to_thread(_guardar_resultado, plano_id, None, str(exc), duracion_ms, modelo_ia)
            return
        duracion_ms = int((time.perf_counter() - t0) * 1000)
        await asyncio.to_thread(_guardar_resultado, plano_id, datos, None, duracion_ms, modelo_ia)
        logger.info(f"IA completada para el plano {plano_id} en {duracion_ms} ms.")


planos_worker = PlanosWorker()

