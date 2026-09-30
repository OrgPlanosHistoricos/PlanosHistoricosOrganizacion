from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import init_db
from .planos_router import router as planos_router
from .planos_worker import planos_worker
from .tasks import task_manager, procesar_directo, ExtraccionError

from .preprocessing import preprocess_image #para PDF

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task_manager.start_worker()
    planos_worker.start()
    yield
    await planos_worker.stop()
    await task_manager.stop_worker()

app = FastAPI(
    title="API de Reconocimiento de Planos Históricos",
    description="Sube un plano escaneado y recibí los datos extraídos en JSON de forma asíncrona.",
    version="1.1.0",
    lifespan=lifespan,
)

app.include_router(planos_router)

# El front se sirve en un origen distinto (nginx en :8080) a la API (:8000),
# así que el navegador bloquea las llamadas sin estos headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FORMATOS_VALIDOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
    "application/pdf",
}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tareas_en_cola": task_manager.queue.qsize(),
    }


@app.post("/procesar-plano", status_code=202)
@app.post("/procesar_plano", status_code=202)
async def procesar_plano(
    archivo: UploadFile = File(...),
    sync: bool = Query(False, description="Si es True, espera la respuesta síncronamente."),
):
    if archivo.content_type not in FORMATOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {archivo.content_type}. "
            f"Usá {', '.join(sorted(FORMATOS_VALIDOS))}.",
        )

    contenido = await archivo.read()

    try:
        imagen_procesada = preprocess_image(contenido, content_type=archivo.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Si se pide síncrono explícitamente (ej: scripts antiguos o curl síncrono)
    if sync:
        try:
            resultado = await procesar_directo(contenido, archivo.filename, archivo.content_type)
            return JSONResponse(content=resultado.model_dump())
        except ExtraccionError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"No se pudo extraer la información del plano: {exc}",
            )

    # Modo asíncrono (predeterminado): responde inmediatamente con HTTP 202 y el ID de tarea
    tarea = task_manager.crear_tarea(archivo.filename or "plano", archivo.content_type, contenido)
    return JSONResponse(
        status_code=202,
        content={
            "task_id": tarea.task_id,
            "status": tarea.status.value,
            "mensaje": "Plano recibido. El procesamiento con IA se está ejecutando en segundo plano.",
        },
    )


@app.get("/tareas/{task_id}")
@app.get("/procesar-plano/{task_id}")
@app.get("/procesar_plano/{task_id}")
def obtener_estado_tarea(task_id: str):
    tarea = task_manager.obtener_tarea(task_id)
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea.to_dict()


@app.get("/tareas")
def listar_tareas():
    return [t.to_dict() for t in task_manager.listar_tareas()]
