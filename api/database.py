"""Conexión a PostgreSQL con SQLModel."""
import os

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (registra las tablas en SQLModel.metadata)

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS texto_extraido TEXT;"))
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS usado_gpu BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE planos ADD COLUMN IF NOT EXISTS tipo_gpu TEXT DEFAULT 'CPU';"))
        conn.commit()


def get_session():
    with Session(engine) as session:
        yield session
