"""Excepciones y manejo de errores de dominio del servicio."""
from fastapi import HTTPException, status


class ExtraccionError(Exception):
    """Error producido durante la inferencia o extracción de datos con el modelo de visión."""
    pass


class ErrorServicio(Exception):
    """Error de dominio que los controladores traducen a HTTPException."""

    def __init__(self, codigo: str, mensaje: str, status_code: int = status.HTTP_400_BAD_REQUEST, detail=None):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.status_code = status_code
        self.detail = detail if detail is not None else mensaje


def a_http(error: ErrorServicio) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)

