"""
Worker en segundo plano que corre la IA sobre los planos creados con POST /planos,
guarda el resultado en la fila correspondiente de Postgres e inserta cada corrida
en la colección corridas_ia de MongoDB.
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from src.compartido import db_client
from src.compartido.minio_client import existe_archivo, obtener_archivo, obtener_preview_key
from src.compartido.preprocessing import pdf_page_to_jpeg_bytes
from src.compartido.sesion import engine
from src.compartido.vision_client import (
    VERSION_PROMPT,
    ExtraccionError,
    extraer_datos_plano,
    limpiar_metadata_corrida,
    obtener_metadata_ultima_corrida,
    obtener_modelo_configurado,
)
from src.models import DatosPlano, EstadoIA, EstadoPlano, Plano, ProcesamientoIA, ahora

logger = logging.getLogger("planos.worker")


def _extraer(image_bytes: bytes) -> dict:
    ultimo_error = None
    # Un reintento: los VLM chicos a veces fallan la primera vez
    for _ in range(2):
        try:
            return extraer_datos_plano(image_bytes).model_dump()
        except ExtraccionError as exc:
            ultimo_error = exc
    raise ExtraccionError(f"No se pudo extraer la información del plano: {ultimo_error}")


def _guardar_corrida_mongo(
    plano_id: int,
    archivo_id: str,
    datos: Optional[dict],
    error: Optional[str],
    corrida_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    info = corrida_info or {}
    json_crudo = info.get("json_crudo")
    if json_crudo is None and datos is not None:
        json_crudo = json.dumps(datos, ensure_ascii=False)

    texto_original = info.get("texto_original")
    if texto_original is None and datos is not None:
        texto_original = datos.get("texto_extraido")

    documento: Dict[str, Any] = {
        "plano_id": plano_id,
        "archivo_id": archivo_id,
        "modelo": info.get("modelo") or obtener_modelo_configurado(),
        "version_prompt": info.get("version_prompt", VERSION_PROMPT),
        "json_crudo": json_crudo,
        "texto_original": texto_original,
        "duracion_segundos": info.get("duracion_segundos", 0.0),
        "fecha": info.get("fecha") or ahora(),
        "estado": EstadoIA.completado.value if datos is not None else EstadoIA.error.value,
        "error": error,
    }

    coleccion = db_client.coleccion_corridas_ia
    if coleccion is not None:
        try:
            coleccion.insert_one(documento)
        except Exception as exc:
            logger.error(f"No se pudo insertar en corridas_ia para el plano {plano_id}: {exc}")

    return documento


def _guardar_resultado(
    plano_id: int,
    datos: Optional[dict],
    error: Optional[str],
    corrida_info: Optional[Dict[str, Any]] = None,
) -> None:
    archivo_id = ""
    with Session(engine) as session:
        plano = session.get(Plano, plano_id)
        if plano is None:
            return

        archivo_id = plano.minio_path
        ultimo_procesamiento = session.exec(
            select(ProcesamientoIA)
            .where(ProcesamientoIA.plano_id == plano_id)
            .order_by(ProcesamientoIA.intento.desc())
        ).first()

        if datos is None:
            plano.ia_estado = EstadoIA.error
            plano.ia_error = error
            if ultimo_procesamiento:
                ultimo_procesamiento.estado = EstadoIA.error
                ultimo_procesamiento.error = error
                session.add(ultimo_procesamiento)
        else:
            if plano.estado != EstadoPlano.pendiente:
                plano.ia_propuesta = json.dumps(datos)
            else:
                for campo in DatosPlano.model_fields:
                    setattr(plano, campo, datos.get(campo))
            plano.ia_estado = EstadoIA.completado
            plano.ia_error = None
            if ultimo_procesamiento:
                ultimo_procesamiento.estado = EstadoIA.completado
                ultimo_procesamiento.error = None
                session.add(ultimo_procesamiento)

        plano.actualizado_en = ahora()
        session.add(plano)
        session.commit()

    _guardar_corrida_mongo(
        plano_id=plano_id,
        archivo_id=archivo_id,
        datos=datos,
        error=error,
        corrida_info=corrida_info,
    )


def _planos_sin_terminar() -> list[tuple[int, bytes]]:
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
                resultado.append((p.id, bytes_img))
            except Exception as exc:
                logger.error(f"No se pudo recuperar archivo del plano pendiente {p.id}: {exc}")
        return resultado


def _ejecutar_extraccion(image_bytes: bytes) -> tuple[Optional[dict], Optional[str], Dict[str, Any]]:
    inicio = time.perf_counter()
    limpiar_metadata_corrida()
    datos: Optional[dict] = None
    error_str: Optional[str] = None
    try:
        datos = _extraer(image_bytes)
    except Exception as exc:
        error_str = str(exc)

    duracion_segundos = round(time.perf_counter() - inicio, 3)
    meta = obtener_metadata_ultima_corrida()
    corrida_info: Dict[str, Any] = {
        "modelo": meta.get("modelo") or obtener_modelo_configurado(),
        "version_prompt": meta.get("version_prompt", VERSION_PROMPT),
        "json_crudo": meta.get("json_crudo"),
        "texto_original": datos.get("texto_extraido") if datos else None,
        "duracion_segundos": duracion_segundos,
        "fecha": ahora(),
    }
    return datos, error_str, corrida_info


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
        datos, error_str, corrida_info = await asyncio.to_thread(_ejecutar_extraccion, image_bytes)
        if datos is None:
            logger.warning(f"IA falló para el plano {plano_id}: {error_str}")
            await asyncio.to_thread(_guardar_resultado, plano_id, None, error_str, corrida_info)
            return
        await asyncio.to_thread(_guardar_resultado, plano_id, datos, None, corrida_info)
        logger.info(f"IA completada para el plano {plano_id}.")


planos_worker = PlanosWorker()
