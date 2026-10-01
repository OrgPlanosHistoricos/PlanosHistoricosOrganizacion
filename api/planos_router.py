"""Endpoints CRUD del catálogo de planos (Postgres + MinIO)."""
import asyncio
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import String, cast, or_
from sqlmodel import Session, select

from .database import engine, get_session
from .minio_client import borrar_archivo, obtener_archivo, subir_archivo
from .models import (
    DatosPlano,
    EstadoIA,
    EstadoPlano,
    HistorialModificacion,
    Plano,
    PlanoDetalle,
    PlanoModificar,
    PlanoRead,
    PlanoValidar,
    ahora,
)
from .planos_worker import planos_worker

router = APIRouter(prefix="/planos", tags=["planos"])

FORMATOS_IMAGEN = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
# Los PDF se guardan pero no pasan por la IA: se catalogan a mano
FORMATOS_ACEPTADOS = FORMATOS_IMAGEN | {"application/pdf"}


def _obtener_plano(session: Session, plano_id: int) -> Plano:
    plano = session.get(Plano, plano_id)
    if plano is None:
        raise HTTPException(status_code=404, detail="Plano no encontrado")
    return plano


def _aplicar_datos(plano: Plano, datos: PlanoValidar | PlanoModificar) -> None:
    for campo in DatosPlano.model_fields:
        setattr(plano, campo, getattr(datos, campo))
    plano.parcela = datos.parcela.strip()
    plano.estado = EstadoPlano.validado if plano.parcela else EstadoPlano.sin_ubicacion
    plano.actualizado_en = ahora()


def _insertar_plano(plano: Plano) -> PlanoRead:
    with Session(engine) as session:
        session.add(plano)
        session.commit()
        session.refresh(plano)
        return PlanoRead.model_validate(plano)


@router.post("", response_model=PlanoRead, status_code=201)
async def crear_plano(
    archivo: UploadFile = File(...),
    ubicacion_fisica: str = Form(""),
    expediente: str = Form(""),
    direccion_referencia: str = Form(""),
):
    if archivo.content_type not in FORMATOS_ACEPTADOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {archivo.content_type}. "
            f"Usá {', '.join(sorted(FORMATOS_ACEPTADOS))}.",
        )

    contenido = await archivo.read()
    nombre = archivo.filename or "plano"
    minio_path = await asyncio.to_thread(subir_archivo, contenido, nombre, archivo.content_type)

    analizable = archivo.content_type in FORMATOS_IMAGEN
    plano = await asyncio.to_thread(
        _insertar_plano,
        Plano(
            nombre_original=nombre,
            content_type=archivo.content_type,
            minio_path=minio_path,
            ubicacion_fisica=ubicacion_fisica.strip(),
            expediente=expediente.strip(),
            direccion_referencia=direccion_referencia.strip(),
            ia_estado=EstadoIA.procesando if analizable else EstadoIA.no_aplica,
        ),
    )

    if analizable:
        planos_worker.encolar(plano.id, contenido)
    return plano


@router.get("", response_model=List[PlanoRead])
def listar_planos(
    estado: Optional[List[EstadoPlano]] = Query(None, description="Se puede repetir: ?estado=validado&estado=sin_ubicacion"),
    q: Optional[str] = Query(None, description="Búsqueda de texto en dirección, parcela, expediente, ubicación, arquitecto, título y año"),
    session: Session = Depends(get_session),
):
    consulta = select(Plano).order_by(Plano.creado_en.desc())
    if estado:
        consulta = consulta.where(Plano.estado.in_(estado))
    if q and q.strip():
        patron = f"%{q.strip()}%"
        consulta = consulta.where(
            or_(
                Plano.direccion_referencia.ilike(patron),
                Plano.parcela.ilike(patron),
                Plano.expediente.ilike(patron),
                Plano.ubicacion_fisica.ilike(patron),
                Plano.arquitecto.ilike(patron),
                Plano.titulo.ilike(patron),
                Plano.ubicacion.ilike(patron),
                cast(Plano.anio, String).ilike(patron),
            )
        )
    return [PlanoRead.model_validate(p) for p in session.exec(consulta).all()]


@router.get("/{plano_id}", response_model=PlanoDetalle)
def obtener_plano(plano_id: int, session: Session = Depends(get_session)):
    return PlanoDetalle.model_validate(_obtener_plano(session, plano_id))


@router.get("/{plano_id}/archivo")
def descargar_archivo(plano_id: int, session: Session = Depends(get_session)):
    plano = _obtener_plano(session, plano_id)
    contenido = obtener_archivo(plano.minio_path)
    return Response(
        content=contenido,
        media_type=plano.content_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(plano.nombre_original)}"},
    )


@router.put("/{plano_id}/validar", response_model=PlanoDetalle)
def validar_plano(plano_id: int, datos: PlanoValidar, session: Session = Depends(get_session)):
    plano = _obtener_plano(session, plano_id)
    if plano.estado != EstadoPlano.pendiente:
        raise HTTPException(
            status_code=409,
            detail="El plano ya fue validado. Usá PUT /planos/{id}/modificar para cambiarlo.",
        )
    _aplicar_datos(plano, datos)
    session.add(plano)
    session.add(HistorialModificacion(plano_id=plano.id, motivo="Validación inicial"))
    session.commit()
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


@router.put("/{plano_id}/modificar", response_model=PlanoDetalle)
def modificar_plano(plano_id: int, datos: PlanoModificar, session: Session = Depends(get_session)):
    motivo = datos.motivo.strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo de la modificación es obligatorio.")
    plano = _obtener_plano(session, plano_id)
    _aplicar_datos(plano, datos)
    session.add(plano)
    session.add(HistorialModificacion(plano_id=plano.id, motivo=motivo))
    session.commit()
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


@router.delete("/{plano_id}", status_code=204)
def eliminar_plano(plano_id: int, session: Session = Depends(get_session)):
    plano = _obtener_plano(session, plano_id)
    if plano.minio_path:
        borrar_archivo(plano.minio_path)
    session.delete(plano)
    session.commit()
    return Response(status_code=204)

