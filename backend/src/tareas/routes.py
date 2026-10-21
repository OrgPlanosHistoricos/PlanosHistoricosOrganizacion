"""Rutas de procesamiento de planos en cola y consulta de tareas (/procesar-plano y /tareas)."""
from fastapi import APIRouter, File, Query, UploadFile

from src.tareas import controllers

router = APIRouter(tags=["tareas"])


@router.post("/procesar-plano", status_code=202)
@router.post("/procesar_plano", status_code=202)
async def procesar_plano(
    archivo: UploadFile = File(...),
    sync: bool = Query(False, description="Si es True, espera la respuesta síncronamente."),
):
    return await controllers.procesar_plano(archivo, sync=sync)


@router.get("/tareas/{task_id}")
@router.get("/procesar-plano/{task_id}")
@router.get("/procesar_plano/{task_id}")
def obtener_estado_tarea(task_id: str):
    return controllers.obtener_estado_tarea(task_id)


@router.get("/tareas")
def listar_tareas():
    return controllers.listar_tareas()

