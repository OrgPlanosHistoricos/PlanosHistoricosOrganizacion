"""Controladores HTTP <-> servicio del recurso /planos."""
from typing import List, Optional
from urllib.parse import quote

from fastapi import Response, UploadFile
from sqlmodel import Session

from src.models import EstadoPlano
from src.planos import services
from src.planos.schemas import PlanoDetalle, PlanoModificar, PlanoRead, PlanoValidar


async def crear_plano(
    archivo: UploadFile,
    circunscripcion: str,
    seccion: str,
    manzana: str,
    parcela_catastral: str,
    ubicacion_fisica: str,
    expediente: str,
    direccion_referencia: str,
    usuario_id: str,
    session: Session,
    ip_origen: Optional[str] = None,
) -> PlanoRead:
    return await services.crear_plano(
        archivo=archivo,
        circunscripcion=circunscripcion,
        seccion=seccion,
        manzana=manzana,
        parcela_catastral=parcela_catastral,
        ubicacion_fisica=ubicacion_fisica,
        expediente=expediente,
        direccion_referencia=direccion_referencia,
        usuario_id=usuario_id,
        session=session,
        ip_origen=ip_origen,
    )


def listar_planos(
    estado: Optional[List[EstadoPlano]],
    q: Optional[str],
    session: Session,
) -> List[PlanoRead]:
    return services.listar_planos(estado=estado, q=q, session=session)


def obtener_plano(plano_id: int, session: Session) -> PlanoDetalle:
    return services.obtener_plano(plano_id=plano_id, session=session)


def eliminar_plano(
    plano_id: int,
    session: Session,
    usuario_id: str = "Operador",
    ip_origen: Optional[str] = None,
) -> dict:
    return services.eliminar_plano(
        plano_id=plano_id,
        session=session,
        usuario_id=usuario_id,
        ip_origen=ip_origen,
    )


def descargar_archivo(plano_id: int, session: Session) -> Response:
    contenido, content_type, nombre_original = services.obtener_archivo_plano(
        plano_id=plano_id, session=session
    )
    return Response(
        content=contenido,
        media_type=content_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(nombre_original)}"},
    )


def obtener_preview(plano_id: int, session: Session) -> Response:
    contenido, media_type = services.obtener_preview_plano(plano_id=plano_id, session=session)
    return Response(
        content=contenido,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


def validar_plano(
    plano_id: int,
    datos: PlanoValidar,
    session: Session,
    ip_origen: Optional[str] = None,
) -> PlanoDetalle:
    return services.validar_plano(
        plano_id=plano_id,
        datos=datos,
        session=session,
        ip_origen=ip_origen,
    )


def modificar_plano(
    plano_id: int,
    datos: PlanoModificar,
    session: Session,
    ip_origen: Optional[str] = None,
) -> PlanoDetalle:
    return services.modificar_plano(
        plano_id=plano_id,
        datos=datos,
        session=session,
        ip_origen=ip_origen,
    )


def descartar_propuesta(plano_id: int, session: Session) -> PlanoDetalle:
    return services.descartar_propuesta(plano_id=plano_id, session=session)


def reintentar_ia(
    plano_id: int,
    usuario_id: str,
    session: Session,
    ip_origen: Optional[str] = None,
) -> PlanoDetalle:
    return services.reintentar_ia(
        plano_id=plano_id,
        usuario_id=usuario_id,
        session=session,
        ip_origen=ip_origen,
    )

