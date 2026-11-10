"""Excepciones y manejo de errores de dominio del servicio."""
from fastapi import HTTPException, status


class ExtraccionError(Exception):
    """Error producido durante la inferencia o extracción de datos con el modelo de visión."""
    pass


class ErrorServicio(Exception):
    """Error de dominio que los controladores traducen a HTTPException."""

    def __init__(self, codigo: str, mensaje: str, status_code: int = status.HTTP_400_BAD_REQUEST, detail=None):
        super().__init__(mensaje)
        self._codigo = codigo
        self._mensaje = mensaje
        self._status_code = status_code
        self._detail = detail if detail is not None else mensaje

    def get_codigo(self) -> str:
        return self._codigo

    def set_codigo(self, valor: str) -> None:
        self._codigo = valor

    def get_mensaje(self) -> str:
        return self._mensaje

    def set_mensaje(self, valor: str) -> None:
        self._mensaje = valor

    def get_status_code(self) -> int:
        return self._status_code

    def set_status_code(self, valor: int) -> None:
        self._status_code = valor

    def get_detail(self):
        return self._detail

    def set_detail(self, valor) -> None:
        self._detail = valor

    codigo = property(get_codigo, set_codigo)
    mensaje = property(get_mensaje, set_mensaje)
    status_code = property(get_status_code, set_status_code)
    detail = property(get_detail, set_detail)


def a_http(error: ErrorServicio) -> HTTPException:
    return HTTPException(status_code=error.get_status_code(), detail=error.get_detail())

