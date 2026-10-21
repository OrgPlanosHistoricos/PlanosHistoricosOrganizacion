"""Servicios y reglas de negocio del catálogo de planos (Postgres + MinIO)."""
import asyncio
from typing import List, Optional, Tuple, Union

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.compartido.minio_client import (
    eliminar_archivo,
    existe_archivo,
    obtener_archivo,
    obtener_preview_key,
    subir_archivo,
    subir_archivo_con_key,
)
from src.compartido.preprocessing import pdf_page_to_jpeg_bytes
from src.compartido.sesion import engine
from src.config import settings
from src.models import (
    DatosPlano,
    EstadoIA,
    EstadoPlano,
    EventoAuditoria,
    Plano,
    ProcesamientoIA,
    ahora,
)
from src.planos.nomenclatura import (
    CAMPOS_NOMENCLATURA,
    clave_nomenclatura,
    normalizar_busqueda,
    normalizar_nomenclatura,
)
from src.planos.schemas import PlanoDetalle, PlanoModificar, PlanoRead, PlanoValidar
from src.planos.worker import planos_worker

FORMATOS_IMAGEN = settings.FORMATOS_IMAGEN
FORMATOS_PDF = settings.FORMATOS_PDF
FORMATOS_ACEPTADOS = settings.FORMATOS_ACEPTADOS


def _obtener_plano(session: Session, plano_id: int) -> Plano:
    plano = session.get(Plano, plano_id)
    if plano is None:
        raise HTTPException(status_code=404, detail="Plano no encontrado")
    return plano


def _datos_nomenclatura(circ, secc, mza, parc):
    try:
        return normalizar_nomenclatura(circ, secc, mza, parc)
    except ValueError:
        raise HTTPException(status_code=422, detail={"codigo": "nomenclatura"})


def _comprobar_unica(session: Session, clave: str, plano_id: Optional[int] = None):
    existente = session.exec(select(Plano).where(Plano.nomenclatura == clave)).first()
    if existente is not None and existente.id != plano_id:
        raise HTTPException(status_code=409, detail={"codigo": "duplicado"})


def _commit_unico(session: Session, clave: str, plano_id: Optional[int] = None):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _comprobar_unica(session, clave, plano_id)
        raise


def _aplicar_datos(plano: Plano, datos: Union[PlanoValidar, PlanoModificar], session: Session) -> None:
    nomen = _datos_nomenclatura(*(getattr(datos, c) for c in CAMPOS_NOMENCLATURA))
    clave = clave_nomenclatura(nomen)
    _comprobar_unica(session, clave, plano.id)
    for campo, valor in nomen.items():
        setattr(plano, campo, valor)
    plano.nomenclatura = clave
    for campo in DatosPlano.model_fields:
        # La transcripción original pertenece al análisis IA, no a la catalogación.
        if campo == "texto_extraido":
            continue
        setattr(plano, campo, getattr(datos, campo))
    plano.estado = EstadoPlano.validado
    plano.actualizado_en = ahora()


def _insertar_plano(plano: Plano) -> PlanoRead:
    with Session(engine) as session:
        session.add(plano)
        session.commit()
        session.refresh(plano)
        return PlanoRead.model_validate(plano)


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
) -> PlanoRead:
    nomen = _datos_nomenclatura(circunscripcion, seccion, manzana, parcela_catastral)
    clave = clave_nomenclatura(nomen)
    _comprobar_unica(session, clave)
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
        **nomen,
        nomenclatura=clave,
        nombre_original=nombre,
        content_type=archivo.content_type,
        minio_path=minio_path,
        ubicacion_fisica=ubicacion_fisica.strip(),
        expediente=expediente.strip(),
        direccion_referencia=direccion_referencia.strip(),
        ia_estado=EstadoIA.procesando,
        creado_por=usuario_id,
    )

    session.add(nuevo_plano)
    nuevo_plano.eventos.append(EventoAuditoria(motivo="Creación de plano", usuario_id=usuario_id))
    nuevo_plano.procesamientos.append(ProcesamientoIA(intento=1, estado=EstadoIA.procesando))
    _commit_unico(session, clave)
    session.refresh(nuevo_plano)

    # Si es PDF, encolamos los bytes renderizados de la primera página.
    # Si es imagen, encolamos el contenido original.
    bytes_para_ia = preview_bytes if es_pdf else contenido
    planos_worker.encolar(nuevo_plano.id, bytes_para_ia)
    return PlanoRead.model_validate(nuevo_plano)


def listar_planos(
    estado: Optional[List[EstadoPlano]],
    q: Optional[str],
    session: Session,
) -> List[PlanoRead]:
    consulta = select(Plano).order_by(Plano.creado_en.desc())
    if estado:
        consulta = consulta.where(Plano.estado.in_(estado))
    if q and q.strip():
        try:
            clave = normalizar_busqueda(q)
        except ValueError:
            raise HTTPException(status_code=422, detail={"codigo": "nomenclatura"})
        consulta = consulta.where(Plano.nomenclatura == clave)
    return [PlanoRead.model_validate(p) for p in session.exec(consulta).all()]


def obtener_plano(plano_id: int, session: Session) -> PlanoDetalle:
    return PlanoDetalle.model_validate(_obtener_plano(session, plano_id))


def eliminar_plano(plano_id: int, session: Session) -> dict:
    plano = session.exec(select(Plano).where(Plano.id == plano_id).with_for_update()).first()
    if plano is None:
        raise HTTPException(status_code=404, detail="Plano no encontrado")
    try:
        eliminar_archivo(obtener_preview_key(plano.minio_path))
        eliminar_archivo(plano.minio_path)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=503, detail="No se pudo eliminar el archivo. Reintentá la operación.")
    for evento in list(plano.eventos):
        session.delete(evento)
    for procesamiento in list(plano.procesamientos):
        session.delete(procesamiento)
    session.delete(plano)
    session.commit()
    return {"eliminado": True, "id": plano_id}


def obtener_archivo_plano(plano_id: int, session: Session) -> Tuple[bytes, str, str]:
    plano = _obtener_plano(session, plano_id)
    contenido = obtener_archivo(plano.minio_path)
    return contenido, plano.content_type, plano.nombre_original


def obtener_preview_plano(plano_id: int, session: Session) -> Tuple[bytes, str]:
    plano = _obtener_plano(session, plano_id)
    if plano.content_type in FORMATOS_IMAGEN:
        contenido = obtener_archivo(plano.minio_path)
        return contenido, plano.content_type

    # Si es PDF, buscar o generar la vista previa JPEG en MinIO
    preview_key = obtener_preview_key(plano.minio_path)
    if existe_archivo(preview_key):
        contenido = obtener_archivo(preview_key)
    else:
        pdf_bytes = obtener_archivo(plano.minio_path)
        contenido = pdf_page_to_jpeg_bytes(pdf_bytes, page_index=0)
        subir_archivo_con_key(contenido, preview_key, "image/jpeg")

    return contenido, "image/jpeg"


def validar_plano(plano_id: int, datos: PlanoValidar, session: Session) -> PlanoDetalle:
    plano = _obtener_plano(session, plano_id)
    if plano.estado != EstadoPlano.pendiente:
        raise HTTPException(
            status_code=409,
            detail="El plano ya fue validado. Usá PUT /planos/{id}/modificar para cambiarlo.",
        )
    _aplicar_datos(plano, datos, session)
    plano.validado_por = datos.usuario_id
    session.add(plano)
    session.add(EventoAuditoria(plano_id=plano.id, motivo="Validación inicial", usuario_id=datos.usuario_id))
    _commit_unico(session, plano.nomenclatura, plano.id)
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


def modificar_plano(plano_id: int, datos: PlanoModificar, session: Session) -> PlanoDetalle:
    motivo = datos.motivo.strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo de la modificación es obligatorio.")
    plano = _obtener_plano(session, plano_id)
    _aplicar_datos(plano, datos, session)
    plano.ia_propuesta = None
    session.add(plano)
    session.add(EventoAuditoria(plano_id=plano.id, motivo=motivo, usuario_id=datos.usuario_id))
    _commit_unico(session, plano.nomenclatura, plano.id)
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


def descartar_propuesta(plano_id: int, session: Session) -> PlanoDetalle:
    plano = _obtener_plano(session, plano_id)
    plano.ia_propuesta = None
    session.add(plano)
    session.commit()
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


def reintentar_ia(plano_id: int, usuario_id: str, session: Session) -> PlanoDetalle:
    plano = _obtener_plano(session, plano_id)
    if plano.ia_estado == EstadoIA.no_aplica:
        raise HTTPException(
            status_code=400,
            detail="El plano no aplica para análisis automático.",
        )
    if plano.ia_estado == EstadoIA.procesando:
        raise HTTPException(
            status_code=400,
            detail="El plano ya está siendo procesado por la IA.",
        )

    intentos_previos = session.exec(select(ProcesamientoIA).where(ProcesamientoIA.plano_id == plano.id)).all()
    max_intento_previo = max([p.intento for p in intentos_previos], default=0)
    num_intentos = max(max_intento_previo, 1 if plano.ia_estado in (EstadoIA.completado, EstadoIA.error) else 0)
    max_intentos = 3
    if num_intentos >= max_intentos:
        raise HTTPException(
            status_code=400,
            detail={"codigo": "max_intentos", "mensaje": f"Se alcanzó el límite máximo de {max_intentos} intentos."},
        )

    nuevo_intento_num = num_intentos + 1
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
