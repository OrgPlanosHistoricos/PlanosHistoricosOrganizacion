"""Servicios generales de salud del sistema y comprobación de base de datos."""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.compartido.sesion import engine
from src.planos.worker import planos_worker


def estado_servicio() -> dict:
    return {
        "status": "ok",
        "tareas_en_cola": planos_worker.queue.qsize(),
    }


def verificar_conexion_db() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False

