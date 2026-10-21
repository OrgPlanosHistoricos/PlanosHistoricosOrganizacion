"""Punto de entrada principal de la aplicación FastAPI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.compartido.sesion import init_db
from src.config import settings
from src.planos.routes import router as planos_router
from src.planos.worker import planos_worker
from src.routes import router as health_router
from src.tareas.routes import router as tareas_router
from src.tareas.services import task_manager


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

ROUTERS_POR_RECURSO = [
    planos_router,
    tareas_router,
]

app.include_router(health_router)
for _router in ROUTERS_POR_RECURSO:
    app.include_router(_router)

# El front se sirve en un origen distinto (nginx en :8080) a la API (:8000),
# así que el navegador bloquea las llamadas sin estos headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

