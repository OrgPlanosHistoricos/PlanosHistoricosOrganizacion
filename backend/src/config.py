"""Configuración central de la API de Planos Históricos."""
import os
from dotenv import load_dotenv

load_dotenv()


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


class Settings:
    def __init__(self) -> None:
        self._cors_origins: list[str] = _lista(os.getenv("CORS_ORIGINS", "*"))
        self._formatos_imagen: set[str] = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
        self._formatos_pdf: set[str] = {"application/pdf"}
        self._formatos_aceptados: set[str] = self._formatos_imagen | self._formatos_pdf
        # Código de tramitacion.localidades donde se buscan los inmuebles de nuestros planos.
        self._localidad_planos: str = os.getenv("LOCALIDAD_PLANOS", "LP")

    def get_cors_origins(self) -> list[str]:
        return self._cors_origins

    def set_cors_origins(self, valor: list[str]) -> None:
        self._cors_origins = valor

    def get_formatos_imagen(self) -> set[str]:
        return self._formatos_imagen

    def set_formatos_imagen(self, valor: set[str]) -> None:
        self._formatos_imagen = valor

    def get_formatos_pdf(self) -> set[str]:
        return self._formatos_pdf

    def set_formatos_pdf(self, valor: set[str]) -> None:
        self._formatos_pdf = valor

    def get_formatos_aceptados(self) -> set[str]:
        return self._formatos_aceptados

    def set_formatos_aceptados(self, valor: set[str]) -> None:
        self._formatos_aceptados = valor

    def get_localidad_planos(self) -> str:
        return self._localidad_planos

    def set_localidad_planos(self, valor: str) -> None:
        self._localidad_planos = valor

    CORS_ORIGINS = property(get_cors_origins, set_cors_origins)
    FORMATOS_IMAGEN = property(get_formatos_imagen, set_formatos_imagen)
    FORMATOS_PDF = property(get_formatos_pdf, set_formatos_pdf)
    FORMATOS_ACEPTADOS = property(get_formatos_aceptados, set_formatos_aceptados)
    LOCALIDAD_PLANOS = property(get_localidad_planos, set_localidad_planos)


settings = Settings()

