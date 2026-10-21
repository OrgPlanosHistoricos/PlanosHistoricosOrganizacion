"""Controladores para el procesamiento directo/asíncrono de planos y consulta de tareas."""
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.config import settings
from src.errors import ExtraccionError
from src.tareas.services import procesar_directo, task_manager


async def procesar_plano(archivo: UploadFile, sync: bool = False) -> JSONResponse:
    if archivo.content_type not in settings.FORMATOS_ACEPTADOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {archivo.content_type}. "
            f"Usá {', '.join(settings.FORMATOS_ACEPTADOS)}.",
        )

    contenido = await archivo.read()

    if sync:
        try:
            resultado = await procesar_directo(contenido, archivo.filename, archivo.content_type)
            return JSONResponse(content=resultado.model_dump())
        except ExtraccionError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"No se pudo extraer la información del plano: {exc}",
            )

    tarea = task_manager.crear_tarea(archivo.filename or "plano", archivo.content_type, contenido)
    return JSONResponse(
        status_code=202,
        content={
            "task_id": tarea.task_id,
            "status": tarea.status.value,
            "mensaje": "Plano recibido. El procesamiento con IA se está ejecutando en segundo plano.",
        },
    )


def obtener_estado_tarea(task_id: str) -> dict:
    tarea = task_manager.obtener_tarea(task_id)
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea.to_dict()


def listar_tareas() -> list[dict]:
    return [t.to_dict() for t in task_manager.listar_tareas()]

