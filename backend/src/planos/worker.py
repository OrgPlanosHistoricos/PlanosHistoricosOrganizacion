"""
Worker en segundo plano que corre la IA sobre los planos creados con POST /planos,
guarda el resultado en la fila correspondiente de Postgres y registra cada corrida
en procesamientos_ia (incluida la respuesta cruda del modelo).
"""
import asyncio
import json
import logging
import time
from typing import Optional

from sqlmodel import Session, select

from src.compartido.storage_client import existe_archivo, obtener_archivo, obtener_preview_key
from src.compartido.preprocessing import MAX_CAJETIN_DIMENSION, MAX_DIMENSION, pdf_page_to_jpeg_bytes
from src.compartido.sesion import engine
from src.compartido.vision_client import (
    VERSION_PROMPT_EXTRACCION,
    ExtraccionError,
    extraer_datos_plano,
    limpiar_metadata_corrida,
    obtener_metadata_ultima_corrida,
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
    json_crudo: Optional[str] = None,
) -> None:
    with Session(engine) as session:
        plano = session.get(Plano, plano_id)
        if plano is None:
            return

        ultimo_procesamiento = session.exec(
            select(ProcesamientoIA)
            .where(ProcesamientoIA.plano_id == plano_id)
            .order_by(ProcesamientoIA.intento.desc())
        ).first()

        if datos is None:
            plano.set_ia_estado(EstadoIA.error)
            plano.set_ia_error(error)
            if ultimo_procesamiento:
                ultimo_procesamiento.set_estado(EstadoIA.error)
                ultimo_procesamiento.set_error(error)
                session.add(ultimo_procesamiento)
        else:
            if plano.get_estado() != EstadoPlano.pendiente:
                plano.set_ia_propuesta(json.dumps(datos, ensure_ascii=False))
            else:
                for campo in DatosPlano.model_fields:
                    setter = getattr(plano, f"set_{campo}", None)
                    if setter:
                        setter(datos.get(campo))
                    else:
                        setattr(plano, campo, datos.get(campo))
            plano.set_ia_estado(EstadoIA.completado)
            plano.set_ia_error(None)
            if ultimo_procesamiento:
                ultimo_procesamiento.set_estado(EstadoIA.completado)
                ultimo_procesamiento.set_error(None)
                session.add(ultimo_procesamiento)

        plano.set_actualizado_en(ahora())
        session.add(plano)

        # Actualizar el registro de ProcesamientoIA correspondiente al último intento
        proc = session.exec(
            select(ProcesamientoIA)
            .where(ProcesamientoIA.plano_id == plano_id)
            .order_by(ProcesamientoIA.intento.desc(), ProcesamientoIA.id.desc())
        ).first()
        if proc is not None:
            proc.set_estado(EstadoIA.error if datos is None else EstadoIA.completado)
            proc.set_error(error)
            if modelo_ia:
                proc.set_modelo_ia(modelo_ia)
            proc.set_version_prompt(VERSION_PROMPT_EXTRACCION)
            proc.set_parametros_preprocesamiento(_parametros_preprocesamiento_default())
            if duracion_ms is not None:
                proc.set_duracion_ms(duracion_ms)
            if datos is not None:
                proc.set_texto_extraido_raw(datos.get("texto_extraido"))
            # Respuesta tal cual la devolvió el modelo (también si no se pudo parsear)
            proc.set_respuesta_json_raw(json_crudo or (json.dumps(datos, ensure_ascii=False) if datos else None))
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
                if p.get_content_type() == "application/pdf":
                    preview_key = obtener_preview_key(p.get_minio_path())
                    if existe_archivo(preview_key):
                        bytes_img = obtener_archivo(preview_key)
                    else:
                        pdf_bytes = obtener_archivo(p.get_minio_path())
                        bytes_img = pdf_page_to_jpeg_bytes(pdf_bytes, page_index=0)
                else:
                    bytes_img = obtener_archivo(p.get_minio_path())
                resultado.append((p.get_id(), bytes_img))
            except Exception as exc:
                logger.error(f"No se pudo recuperar archivo del plano pendiente {p.get_id()}: {exc}")
        return resultado


def _ejecutar_extraccion(image_bytes: bytes) -> tuple[Optional[dict], Optional[str], Optional[str]]:
    limpiar_metadata_corrida()
    datos: Optional[dict] = None
    error_str: Optional[str] = None
    try:
        datos = _extraer(image_bytes)
    except Exception as exc:
        error_str = str(exc)

    return datos, error_str, obtener_metadata_ultima_corrida().get("json_crudo")


class PlanosWorker:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    def get_queue(self) -> asyncio.Queue:
        return self._queue

    def set_queue(self, valor: asyncio.Queue) -> None:
        self._queue = valor

    def get_task(self) -> Optional[asyncio.Task]:
        return self._task

    def set_task(self, valor: Optional[asyncio.Task]) -> None:
        self._task = valor

    queue = property(get_queue, set_queue)

    def start(self) -> None:
        if self.get_task() is None or self.get_task().done():
            self.set_task(asyncio.create_task(self._loop()))

    async def stop(self) -> None:
        tarea = self.get_task()
        if tarea:
            tarea.cancel()
            try:
                await tarea
            except asyncio.CancelledError:
                pass
            self.set_task(None)

    def encolar(self, plano_id: int, image_bytes: bytes) -> None:
        self.get_queue().put_nowait((plano_id, image_bytes))

    async def _loop(self) -> None:
        # La cola vive en memoria: lo que quedó a medias antes de un reinicio se retoma acá
        try:
            for plano_id, image_bytes in await asyncio.to_thread(_planos_sin_terminar):
                self.encolar(plano_id, image_bytes)
        except Exception:
            logger.exception("No se pudieron recuperar los planos pendientes de IA")

        while True:
            plano_id, image_bytes = await self.get_queue().get()
            try:
                await self._procesar(plano_id, image_bytes)
            except Exception:
                logger.exception(f"Error guardando el resultado de IA del plano {plano_id}")
            finally:
                self.get_queue().task_done()

    async def _procesar(self, plano_id: int, image_bytes: bytes) -> None:
        logger.info(f"Procesando IA del plano {plano_id}...")
        t0 = time.perf_counter()
        modelo_ia = await asyncio.to_thread(obtener_modelo_activo)
        datos, error_str, json_crudo = await asyncio.to_thread(_ejecutar_extraccion, image_bytes)
        duracion_ms = int((time.perf_counter() - t0) * 1000)
        if datos is None:
            logger.warning(f"IA falló para el plano {plano_id}: {error_str}")
            await asyncio.to_thread(
                _guardar_resultado,
                plano_id,
                None,
                error_str,
                duracion_ms=duracion_ms,
                modelo_ia=modelo_ia,
                json_crudo=json_crudo,
            )
            return
        await asyncio.to_thread(
            _guardar_resultado,
            plano_id,
            datos,
            None,
            duracion_ms=duracion_ms,
            modelo_ia=modelo_ia,
            json_crudo=json_crudo,
        )
        logger.info(f"IA completada para el plano {plano_id} en {duracion_ms} ms.")


planos_worker = PlanosWorker()
