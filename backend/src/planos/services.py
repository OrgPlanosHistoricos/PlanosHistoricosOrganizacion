"""Servicios y reglas de negocio del catálogo de planos (Postgres + Supabase Storage)."""
import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.compartido.storage_client import (
    existe_archivo,
    obtener_archivo,
    obtener_preview_key,
    subir_archivo,
    subir_archivo_con_key,
)
from src.compartido.preprocessing import MAX_CAJETIN_DIMENSION, MAX_DIMENSION, pdf_page_to_jpeg_bytes
from src.compartido.sesion import engine
from src.compartido.vision_client import VERSION_PROMPT_EXTRACCION
from src.config import settings
from src.models import (
    DatosPlano,
    EstadoIA,
    EstadoPlano,
    EventoAuditoria,
    Inmueble,
    Localidad,
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

FORMATOS_IMAGEN = settings.get_formatos_imagen()
FORMATOS_PDF = settings.get_formatos_pdf()
FORMATOS_ACEPTADOS = settings.get_formatos_aceptados()

CAMPOS_AUDITORIA = (
    "texto_extraido",
    "circunscripcion",
    "seccion",
    "manzana",
    "parcela_catastral",
    "nomenclatura",
    "ubicacion_fisica",
    "expediente",
    "direccion_referencia",
    "parcela",
    "arquitecto",
    "anio",
    "titulo",
    "ubicacion",
    "escala",
    "tipo_de_plano",
    "material_soporte",
    "notas",
    "estado",
)


def _snapshot_plano(plano: Plano) -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for campo in CAMPOS_AUDITORIA:
        getter = getattr(plano, f"get_{campo}", None)
        val = getter() if getter else getattr(plano, campo, None)
        if hasattr(val, "value"):
            val = val.value
        snap[campo] = val
    return snap


def _parametros_preprocesamiento_json() -> str:
    return json.dumps(
        {
            "max_dimension_deteccion": MAX_DIMENSION,
            "max_dimension_cajetin": MAX_CAJETIN_DIMENSION,
            "autocontrast_cutoff": 1,
            "sharpness_factor": 1.5,
            "padding_pct": 0.02,
            "rotacion": 0,
        },
        ensure_ascii=False,
    )


def _obtener_plano(session: Session, plano_id: int) -> Plano:
    plano = session.get(Plano, plano_id)
    if plano is None or not plano.get_activo():
        raise HTTPException(status_code=404, detail="Plano no encontrado")
    return plano


def _datos_nomenclatura(circ, secc, mza, parc):
    try:
        return normalizar_nomenclatura(circ, secc, mza, parc)
    except ValueError:
        raise HTTPException(status_code=422, detail={"codigo": "nomenclatura"})


def _comprobar_unica(session: Session, clave: str, plano_id: Optional[int] = None):
    if clave is None:
        return
    existente = session.exec(
        select(Plano).where(Plano.nomenclatura == clave, Plano.activo == True)  # noqa: E712
    ).first()
    if existente is not None and existente.get_id() != plano_id:
        raise HTTPException(status_code=409, detail={"codigo": "duplicado"})


def _buscar_inmueble(session: Session, clave: str) -> Optional[int]:
    """Vincula con el inmueble de tramitación solo si ya existe; nunca lo crea."""
    return session.exec(
        select(Inmueble.id_inmueble)
        .join(Localidad)
        .where(
            Inmueble.nomenclatura_catastral == clave,
            Inmueble.activo == True,  # noqa: E712
            Localidad.codigo == settings.get_localidad_planos(),
        )
    ).first()


def _comprobar_sin_analisis_en_curso(session: Session) -> None:
    en_proceso = session.exec(
        select(Plano).where(Plano.ia_estado == EstadoIA.procesando, Plano.activo == True)  # noqa: E712
    ).first()
    if en_proceso is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "codigo": "procesando_ia",
                "mensaje": "Ya hay un plano en análisis en este momento. Esperá a que finalice antes de subir otro.",
            },
        )


def _commit_unico(session: Session, clave: str, plano_id: Optional[int] = None):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        _comprobar_unica(session, clave, plano_id)
        raise


def _aplicar_datos(plano: Plano, datos: Union[PlanoValidar, PlanoModificar], session: Session) -> None:
    nomen = _datos_nomenclatura(*(getattr(datos, f"get_{c}")() for c in CAMPOS_NOMENCLATURA))
    clave = clave_nomenclatura(nomen)
    _comprobar_unica(session, clave, plano.get_id())
    for campo, valor in nomen.items():
        getattr(plano, f"set_{campo}")(valor)
    plano.set_nomenclatura(clave)
    plano.set_id_inmueble(_buscar_inmueble(session, clave))
    for campo in DatosPlano.model_fields:
        # La transcripción original pertenece al análisis IA, no a la catalogación.
        if campo == "texto_extraido":
            continue
        getattr(plano, f"set_{campo}")(getattr(datos, f"get_{campo}")())
    plano.set_estado(EstadoPlano.validado)
    plano.set_actualizado_en(ahora())


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
    ip_origen: Optional[str] = None,
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
    _comprobar_sin_analisis_en_curso(session)

    contenido = await archivo.read()
    hash_sha256 = hashlib.sha256(contenido).hexdigest()
    tamano_bytes = len(contenido)
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
        id_inmueble=_buscar_inmueble(session, clave),
        nombre_original=nombre,
        content_type=archivo.content_type,
        hash_sha256=hash_sha256,
        tamano_bytes=tamano_bytes,
        minio_path=minio_path,
        ubicacion_fisica=ubicacion_fisica.strip(),
        expediente=expediente.strip(),
        direccion_referencia=direccion_referencia.strip(),
        ia_estado=EstadoIA.procesando,
        creado_por=usuario_id,
    )

    session.add(nuevo_plano)
    nuevo_plano.get_eventos().append(
        EventoAuditoria(
            accion="Carga",
            motivo="Creación de plano",
            usuario_id=usuario_id,
            valores_anteriores=None,
            valores_nuevos=json.dumps(_snapshot_plano(nuevo_plano), ensure_ascii=False),
            ip_origen=ip_origen,
        )
    )
    nuevo_plano.get_procesamientos().append(
        ProcesamientoIA(
            intento=1,
            estado=EstadoIA.procesando,
            version_prompt=VERSION_PROMPT_EXTRACCION,
            parametros_preprocesamiento=_parametros_preprocesamiento_json(),
        )
    )
    _commit_unico(session, clave)
    session.refresh(nuevo_plano)

    # Si es PDF, encolamos los bytes renderizados de la primera página.
    # Si es imagen, encolamos el contenido original.
    bytes_para_ia = preview_bytes if es_pdf else contenido
    planos_worker.encolar(nuevo_plano.get_id(), bytes_para_ia)
    return PlanoRead.model_validate(nuevo_plano)


def listar_planos(
    estado: Optional[List[EstadoPlano]],
    q: Optional[str],
    session: Session,
) -> List[PlanoRead]:
    consulta = select(Plano).where(Plano.activo == True).order_by(Plano.creado_en.desc())  # noqa: E712
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


def eliminar_plano(
    plano_id: int,
    session: Session,
    usuario_id: str = "Operador",
    ip_origen: Optional[str] = None,
) -> dict:
    plano = session.exec(
        select(Plano).where(Plano.id == plano_id, Plano.activo == True).with_for_update()  # noqa: E712
    ).first()
    if plano is None:
        raise HTTPException(status_code=404, detail="Plano no encontrado")
    valores_ant = _snapshot_plano(plano)
    valores_ant["activo"] = True
    plano.set_activo(False)
    plano.set_nomenclatura(None)
    plano.set_actualizado_en(ahora())
    valores_nue = _snapshot_plano(plano)
    valores_nue["activo"] = False
    session.add(plano)
    session.add(
        EventoAuditoria(
            plano_id=plano.get_id(),
            accion="Caducidad",
            motivo="Baja lógica de plano",
            usuario_id=usuario_id,
            valores_anteriores=json.dumps(valores_ant, ensure_ascii=False),
            valores_nuevos=json.dumps(valores_nue, ensure_ascii=False),
            ip_origen=ip_origen,
        )
    )
    session.commit()
    return {"eliminado": True, "id": plano_id}


def obtener_archivo_plano(plano_id: int, session: Session) -> Tuple[bytes, str, str]:
    plano = _obtener_plano(session, plano_id)
    contenido = obtener_archivo(plano.get_minio_path())
    return contenido, plano.get_content_type(), plano.get_nombre_original()


def obtener_preview_plano(plano_id: int, session: Session) -> Tuple[bytes, str]:
    plano = _obtener_plano(session, plano_id)
    if plano.get_content_type() in FORMATOS_IMAGEN:
        contenido = obtener_archivo(plano.get_minio_path())
        return contenido, plano.get_content_type()

    # Si es PDF, buscar o generar la vista previa JPEG en Storage
    preview_key = obtener_preview_key(plano.get_minio_path())
    if existe_archivo(preview_key):
        contenido = obtener_archivo(preview_key)
    else:
        pdf_bytes = obtener_archivo(plano.get_minio_path())
        contenido = pdf_page_to_jpeg_bytes(pdf_bytes, page_index=0)
        subir_archivo_con_key(contenido, preview_key, "image/jpeg")

    return contenido, "image/jpeg"


def validar_plano(
    plano_id: int,
    datos: PlanoValidar,
    session: Session,
    ip_origen: Optional[str] = None,
) -> PlanoDetalle:
    plano = _obtener_plano(session, plano_id)
    if plano.get_estado() != EstadoPlano.pendiente:
        raise HTTPException(
            status_code=409,
            detail="El plano ya fue validado. Usá PUT /planos/{id}/modificar para cambiarlo.",
        )
    valores_ant = _snapshot_plano(plano)
    _aplicar_datos(plano, datos, session)
    plano.set_validado_por(datos.get_usuario_id())
    plano.set_validado_en(ahora())
    valores_nue = _snapshot_plano(plano)
    session.add(plano)
    session.add(
        EventoAuditoria(
            plano_id=plano.get_id(),
            accion="Validación",
            motivo="Validación inicial",
            usuario_id=datos.get_usuario_id(),
            valores_anteriores=json.dumps(valores_ant, ensure_ascii=False),
            valores_nuevos=json.dumps(valores_nue, ensure_ascii=False),
            ip_origen=ip_origen,
        )
    )
    _commit_unico(session, plano.get_nomenclatura(), plano.get_id())
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


def modificar_plano(
    plano_id: int,
    datos: PlanoModificar,
    session: Session,
    ip_origen: Optional[str] = None,
) -> PlanoDetalle:
    motivo = datos.get_motivo().strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo de la modificación es obligatorio.")
    plano = _obtener_plano(session, plano_id)
    valores_ant = _snapshot_plano(plano)
    _aplicar_datos(plano, datos, session)
    # La transcripción solo se actualiza aceptando el valor de la propuesta IA.
    if plano.get_ia_propuesta() and "texto_extraido" in datos.model_fields_set:
        try:
            propuesta = json.loads(plano.get_ia_propuesta())
        except (TypeError, ValueError):
            propuesta = {}
        if isinstance(propuesta, dict) and "texto_extraido" in propuesta:
            texto_ia = propuesta["texto_extraido"] or None
            if datos.get_texto_extraido() == texto_ia:
                plano.set_texto_extraido(texto_ia)
    plano.set_ia_propuesta(None)
    valores_nue = _snapshot_plano(plano)
    session.add(plano)
    session.add(
        EventoAuditoria(
            plano_id=plano.get_id(),
            accion="Modificación",
            motivo=motivo,
            usuario_id=datos.get_usuario_id(),
            valores_anteriores=json.dumps(valores_ant, ensure_ascii=False),
            valores_nuevos=json.dumps(valores_nue, ensure_ascii=False),
            ip_origen=ip_origen,
        )
    )
    _commit_unico(session, plano.get_nomenclatura(), plano.get_id())
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


def descartar_propuesta(plano_id: int, session: Session) -> PlanoDetalle:
    plano = _obtener_plano(session, plano_id)
    plano.set_ia_propuesta(None)
    session.add(plano)
    session.commit()
    session.refresh(plano)
    return PlanoDetalle.model_validate(plano)


def reintentar_ia(
    plano_id: int,
    usuario_id: str,
    session: Session,
    ip_origen: Optional[str] = None,
) -> PlanoDetalle:
    plano = _obtener_plano(session, plano_id)
    if plano.get_ia_estado() == EstadoIA.no_aplica:
        raise HTTPException(
            status_code=400,
            detail="El plano no aplica para análisis automático.",
        )
    if plano.get_ia_estado() == EstadoIA.procesando:
        raise HTTPException(
            status_code=400,
            detail="El plano ya está siendo procesado por la IA.",
        )

    intentos_previos = session.exec(select(ProcesamientoIA).where(ProcesamientoIA.plano_id == plano.get_id())).all()
    max_intento_previo = max([p.get_intento() for p in intentos_previos], default=0)
    num_intentos = max(max_intento_previo, 1 if plano.get_ia_estado() in (EstadoIA.completado, EstadoIA.error) else 0)
    max_intentos = 3
    if num_intentos >= max_intentos:
        raise HTTPException(
            status_code=400,
            detail={"codigo": "max_intentos", "mensaje": f"Se alcanzó el límite máximo de {max_intentos} intentos."},
        )

    nuevo_intento_num = num_intentos + 1
    plano.set_ia_estado(EstadoIA.procesando)
    session.add(plano)

    session.add(
        EventoAuditoria(
            plano_id=plano.get_id(),
            accion="Observación",
            motivo="Reintento de análisis IA",
            usuario_id=usuario_id,
            ip_origen=ip_origen,
        )
    )
    session.add(
        ProcesamientoIA(
            plano_id=plano.get_id(),
            intento=nuevo_intento_num,
            estado=EstadoIA.procesando,
            version_prompt=VERSION_PROMPT_EXTRACCION,
            parametros_preprocesamiento=_parametros_preprocesamiento_json(),
        )
    )
    session.commit()
    session.refresh(plano)

    contenido = obtener_archivo(plano.get_minio_path())
    if plano.get_content_type() in FORMATOS_PDF:
        try:
            contenido = pdf_page_to_jpeg_bytes(contenido, 0)
        except Exception:
            pass

    planos_worker.encolar(plano.get_id(), contenido)
    return PlanoDetalle.model_validate(plano)
