"""Configuración central de la API de Planos Históricos."""
import os
from dotenv import load_dotenv

load_dotenv()


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


class Settings:
    CORS_ORIGINS: list[str] = _lista(os.getenv("CORS_ORIGINS", "*"))
    FORMATOS_IMAGEN: set[str] = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
    FORMATOS_PDF: set[str] = {"application/pdf"}
    FORMATOS_ACEPTADOS: set[str] = FORMATOS_IMAGEN | FORMATOS_PDF


settings = Settings()

