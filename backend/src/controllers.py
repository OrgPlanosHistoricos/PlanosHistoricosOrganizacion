"""Controladores generales de salud del servicio y base de datos."""
from fastapi.responses import JSONResponse

from src import services


def health() -> dict:
    return services.estado_servicio()


def database_health() -> JSONResponse:
    if not services.verificar_conexion_db():
        return JSONResponse(
            status_code=503,
            content={"database": "disconnected"},
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse(
        content={"database": "connected"},
        headers={"Cache-Control": "no-store"},
    )

