"""Comprobación de la base de datos del catálogo."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import engine

router = APIRouter()


@router.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"database": "disconnected"},
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse(
        content={"database": "connected"},
        headers={"Cache-Control": "no-store"},
    )
