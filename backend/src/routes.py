"""Rutas generales de salud y estado de la base de datos (/health y /health/database)."""
from fastapi import APIRouter

from src import controllers

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return controllers.health()


@router.get("/health/database")
def database_health():
    return controllers.database_health()

