"""Endpoints CRUD del catálogo de planos (/planos)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlmodel import Session

from src.compartido.sesion import get_session
from src.models import EstadoPlano
from src.planos import controllers
from src.planos.schemas import PlanoDetalle, PlanoModificar, PlanoRead, PlanoValidar

router = APIRouter(prefix="/planos", tags=["planos"])


def _obtener_ip_origen(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()[:45]
    if request.client and request.client.host:
        return request.client.host[:45]
    return None


@router.post("", response_model=PlanoRead, status_code=201)
async def crear_plano(
    request: Request,
    archivo: UploadFile = File(...),
    circunscripcion: str = Form(...),
    seccion: str = Form(...),
    manzana: str = Form(...),
    parcela_catastral: str = Form(...),
    ubicacion_fisica: str = Form(""),
    expediente: str = Form(""),
    direccion_referencia: str = Form(""),
    usuario_id: str = Form("anonimo", description="ID del usuario que sube el plano"),
    session: Session = Depends(get_session),
):
    return await controllers.crear_plano(
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
        ip_origen=_obtener_ip_origen(request),
    )


@router.get("", response_model=List[PlanoRead])
def listar_planos(
    estado: Optional[List[EstadoPlano]] = Query(None, description="Se puede repetir: ?estado=validado&estado=sin_ubicacion"),
    q: Optional[str] = Query(None, description="Nomenclatura exacta: circunscripción-sección-manzana-parcela"),
    session: Session = Depends(get_session),
):
    return controllers.listar_planos(estado=estado, q=q, session=session)


@router.get("/{plano_id}", response_model=PlanoDetalle)
def obtener_plano(plano_id: int, session: Session = Depends(get_session)):
    return controllers.obtener_plano(plano_id=plano_id, session=session)


@router.delete("/{plano_id}")
def eliminar_plano(
    request: Request,
    plano_id: int,
    usuario_id: str = Query("Operador", description="ID del usuario que elimina el plano"),
    session: Session = Depends(get_session),
):
    return controllers.eliminar_plano(
        plano_id=plano_id,
        session=session,
        usuario_id=usuario_id,
        ip_origen=_obtener_ip_origen(request),
    )


@router.get("/{plano_id}/archivo")
def descargar_archivo(plano_id: int, session: Session = Depends(get_session)):
    return controllers.descargar_archivo(plano_id=plano_id, session=session)


@router.get("/{plano_id}/preview")
def obtener_preview(plano_id: int, session: Session = Depends(get_session)):
    return controllers.obtener_preview(plano_id=plano_id, session=session)


@router.put("/{plano_id}/validar", response_model=PlanoDetalle)
def validar_plano(
    request: Request,
    plano_id: int,
    datos: PlanoValidar,
    session: Session = Depends(get_session),
):
    return controllers.validar_plano(
        plano_id=plano_id,
        datos=datos,
        session=session,
        ip_origen=_obtener_ip_origen(request),
    )


@router.put("/{plano_id}/modificar", response_model=PlanoDetalle)
def modificar_plano(
    request: Request,
    plano_id: int,
    datos: PlanoModificar,
    session: Session = Depends(get_session),
):
    return controllers.modificar_plano(
        plano_id=plano_id,
        datos=datos,
        session=session,
        ip_origen=_obtener_ip_origen(request),
    )


@router.post("/{plano_id}/descartar_propuesta", response_model=PlanoDetalle)
def descartar_propuesta(plano_id: int, session: Session = Depends(get_session)):
    return controllers.descartar_propuesta(plano_id=plano_id, session=session)


@router.post("/{plano_id}/reintentar_ia", response_model=PlanoDetalle)
def reintentar_ia(
    request: Request,
    plano_id: int,
    usuario_id: str = Query(..., description="ID del usuario que solicita el reintento"),
    session: Session = Depends(get_session),
):
    return controllers.reintentar_ia(
        plano_id=plano_id,
        usuario_id=usuario_id,
        session=session,
        ip_origen=_obtener_ip_origen(request),
    )

