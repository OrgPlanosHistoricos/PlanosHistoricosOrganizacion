"""Conexión a PostgreSQL con SQLModel."""
import os

from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (registra las tablas en SQLModel.metadata)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://planos:planos@localhost:5432/planos_db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
