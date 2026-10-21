"""Punto de acceso compartido a la sesión y motor de PostgreSQL."""
from sqlmodel import Session

from src.models import DATABASE_URL, engine, get_session, init_db

__all__ = ["DATABASE_URL", "engine", "get_session", "init_db", "obtener_sesion"]


def obtener_sesion() -> Session:
    return Session(engine)

