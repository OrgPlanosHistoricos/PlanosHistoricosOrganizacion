"""Endpoints CRUD del catálogo de planos (Postgres + MinIO)."""
import asyncio
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import String, cast, or_
from sqlmodel import Session, select

from .database import engine, get_session
from .minio_client import (
    existe_archivo,
    obtener_archivo,
    obtener_preview_key,
    subir_archivo,
    subir_archivo_con_key,
)
from .models import (
    DatosPlano,
    EstadoIA,
    EstadoPlano,
    EventoAuditoria,
    ProcesamientoIA,
    Plano,
    PlanoDetalle,
    PlanoModificar,
    PlanoRead,
    PlanoValidar,
    ahora,
)
from .planos_worker import planos_worker
from .preprocessing import pdf_page_to_jpeg_bytes

router = APIRouter(prefix="/planos", tags=["planos"])

FORMATOS_IMAGEN = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
FORMATOS_PDF = {"application/pdf"}
FORMATOS_ACEPTADOS = FORMATOS_IMAGEN | FORMATOS_PDF


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
    usuario_id: str = Form("anonimo", description="ID del usuario que sube el plano"),
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

    es_pdf = archivo.content_type in FORMATOS_PDF
    preview_bytes = None
    if es_pdf:
        try:
            preview_bytes = await asyncio.to_thread(pdf_page_to_jpeg_bytes, contenido, 0)
            preview_key = obtener_preview_key(minio_path)
            await asyncio.to_thread(subir_archivo_con_key, preview_bytes, preview_key, "image/jpeg")
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo leer o renderizar el archivo PDF: {exc}",
            )

    nuevo_plano = Plano(
        nombre_original=nombre,
        content_type=archivo.content_type,
        minio_path=minio_path,
        ubicacion_fisica=ubicacion_fisica.strip(),
        expediente=expediente.strip(),
        direccion_referencia=direccion_referencia.strip(),
        ia_estado=EstadoIA.procesando,
        creado_por=usuario_id,
    )
    
    with Session(engine) as session:
        session.add(nuevo_plano)
        session.commit()
        session.refresh(nuevo_plano)
        session.add(EventoAuditoria(plano_id=nuevo_plano.id, motivo="Creación de plano", usuario_id=usuario_id))
        
        # Guardar el primer intento de IA
        session.add(ProcesamientoIA(plano_id=nuevo_plano.id, intento=1, estado=EstadoIA.procesando))
        session.commit()
        session.refresh(nuevo_plano)

    # Si es PDF, encolamos los bytes renderizados de la primera página.
    # Si es imagen, encolamos el contenido original.
    bytes_para_ia = preview_bytes if es_pdf else contenido
    planos_worker.encolar(nuevo_plano.id, bytes_para_ia)
    return PlanoRead.model_validate(nuevo_plano)


@router.get("", response_model=List[PlanoRead])
def listar_planos(
    estado: Optional[List[EstadoPlano]] = Query(None, description="Se puede repetir: ?estado=validado&estado=sin_ubicacion"),
    q: Optional[str] = Query(None, description="Búsqueda de texto en dirección, parcela, expediente, ubicación, arquitecto, título, año y texto extraído"),
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
                Plano.texto_extraido.ilike(patron),
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


@router.get("/{plano_id}/preview")
def obtener_preview(plano_id: int, session: Session = Depends(get_session)):
    plano = _obtener_plano(session, plano_id)
    if plano.content_type in FORMATOS_IMAGEN:
        contenido = obtener_archivo(plano.minio_path)
        return Response(
            content=contenido,
            media_type=plano.content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # Si es PDF, buscar o generar la vista previa JPEG en MinIO
    preview_key = obtener_preview_key(plano.minio_path)
    if existe_archivo(preview_key):
        contenido = obtener_archivo(preview_key)
    else:
        pdf_bytes = obtener_archivo(plano.minio_path)
        contenido = pdf_page_to_jpeg_bytes(pdf_bytes, page_index=0)
        subir_archivo_con_key(contenido, preview_key, "image/jpeg")

    return Response(
        content=contenido,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
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
    plano.validado_por = datos.usuario_id
    session.add(plano)
    session.add(EventoAuditoria(plano_id=plano.id, motivo="Validación inicial", usuario_id=datos.usuario_id))
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
    session.add(EventoAuditoria(plano_id=plano.id, motivo=motivo, usuario_id=datos.usuario_id))
    session.commit()
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


@router.post("/{plano_id}/reintentar_ia", response_model=PlanoDetalle)
def reintentar_ia(plano_id: int, usuario_id: str = Query(..., description="ID del usuario que solicita el reintento"), session: Session = Depends(get_session)):
    plano = _obtener_plano(session, plano_id)
    if plano.ia_estado not in (EstadoIA.error, EstadoIA.no_aplica):
        raise HTTPException(
            status_code=400,
            detail="El plano no tiene un análisis fallido o que no aplique.",
        )
    
    intentos_previos = session.exec(select(ProcesamientoIA).where(ProcesamientoIA.plano_id == plano.id)).all()
    max_intentos = 3
    if len(intentos_previos) >= max_intentos:
        raise HTTPException(
            status_code=400,
            detail=f"Se alcanzó el límite máximo de {max_intentos} intentos.",
        )

    nuevo_intento_num = len(intentos_previos) + 1
    plano.ia_estado = EstadoIA.procesando
    session.add(plano)
    
    session.add(EventoAuditoria(plano_id=plano.id, motivo="Reintento de análisis IA", usuario_id=usuario_id))
    session.add(ProcesamientoIA(plano_id=plano.id, intento=nuevo_intento_num, estado=EstadoIA.procesando))
    session.commit()
    session.refresh(plano)
    
    contenido = obtener_archivo(plano.minio_path)
    if plano.content_type in FORMATOS_PDF:
        try:
            contenido = pdf_page_to_jpeg_bytes(contenido, 0)
        except Exception:
            pass
            
    planos_worker.encolar(plano.id, contenido)
    return PlanoDetalle.model_validate(plano)
