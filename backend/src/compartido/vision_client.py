"""
Cliente HTTP hacia Ollama con soporte para extracción en dos pasos:
1. Grounding / Detección del cajetín (carimbo/cuadro técnico) en coordenadas normalizadas [ymin, xmin, ymax, xmax].
2. Recorte del cajetín en alta resolución y extracción estructurada con JSON Schema.
"""
import base64
import io
import json
import logging
import os
from pathlib import Path
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from dotenv import dotenv_values
from PIL import Image
from pydantic import BaseModel, Field
import requests

from src.compartido.preprocessing import crop_cajetin_from_bbox, preprocess_cajetin, preprocess_image
from src.errors import ExtraccionError
from src.tareas.schemas import PlanoHistorico

logger = logging.getLogger("planos.vision")

_ENV_CANDIDATES = (
    Path(__file__).resolve().parents[2] / ".env",  # /app/.env en Docker
    Path(__file__).resolve().parents[3] / ".env",  # raíz del repo en entorno local
)
_ENV_FILE = next((p for p in _ENV_CANDIDATES if p.is_file()), _ENV_CANDIDATES[0])

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
MODEL_NAME = os.environ.get("VISION_MODEL", "qwen2.5vl:3b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
VERSION_PROMPT = "1.0"

_INITIAL_OLLAMA_HOST = OLLAMA_HOST
_INITIAL_MODEL_NAME = MODEL_NAME
_INITIAL_OLLAMA_TIMEOUT = OLLAMA_TIMEOUT

OLLAMA_HEADERS = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
}
COLAB_ACTIVE_ALIAS = "colab-activo"

_ultima_corrida = threading.local()


def limpiar_metadata_corrida() -> None:
    """Reinicia la metadata de la última corrida de IA en el hilo actual."""
    _ultima_corrida.modelo = None
    _ultima_corrida.version_prompt = VERSION_PROMPT
    _ultima_corrida.json_crudo = None


def obtener_metadata_ultima_corrida() -> Dict[str, Any]:
    """Devuelve la metadata registrada en la última ejecución de IA del hilo actual."""
    return {
        "modelo": getattr(_ultima_corrida, "modelo", None) or obtener_modelo_configurado(),
        "version_prompt": getattr(_ultima_corrida, "version_prompt", VERSION_PROMPT),
        "json_crudo": getattr(_ultima_corrida, "json_crudo", None),
    }


def _leer_env_actualizado() -> Dict[str, str]:
    """Lee las variables definidas en el archivo .env si existe en disco."""
    if _ENV_FILE.is_file():
        try:
            return {k: v for k, v in dotenv_values(_ENV_FILE).items() if v is not None}
        except Exception:
            return {}
    return {}


def obtener_ollama_host() -> str:
    """Devuelve el host de Ollama actual, recargando .env si fue actualizado."""
    if OLLAMA_HOST != _INITIAL_OLLAMA_HOST:
        return OLLAMA_HOST.rstrip("/")
    env_file_vars = _leer_env_actualizado()
    host = env_file_vars.get("OLLAMA_HOST") or os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    return host.strip().rstrip("/")


def obtener_modelo_configurado() -> str:
    """Devuelve el modelo por defecto configurado localmente (fallback)."""
    if MODEL_NAME != _INITIAL_MODEL_NAME:
        return MODEL_NAME.strip()
    env_file_vars = _leer_env_actualizado()
    modelo = env_file_vars.get("VISION_MODEL") or os.environ.get("VISION_MODEL", "qwen2.5vl:3b")
    return modelo.strip()


def obtener_ollama_timeout() -> int:
    """Devuelve el timeout configurado para llamadas a Ollama."""
    if OLLAMA_TIMEOUT != _INITIAL_OLLAMA_TIMEOUT:
        return OLLAMA_TIMEOUT
    env_file_vars = _leer_env_actualizado()
    raw_timeout = env_file_vars.get("OLLAMA_TIMEOUT") or os.environ.get("OLLAMA_TIMEOUT", "300")
    try:
        return int(raw_timeout)
    except ValueError:
        return 300


def obtener_modelo_activo(ollama_host: Optional[str] = None) -> str:
    """Detecta dinámicamente el modelo de visión activo en el servidor Ollama (Google Colab o local).

    Prioridad:
    1. Si en Ollama existe el alias 'colab-activo' (creado al elegir modelo en el notebook de Colab),
       resuelve el nombre real del modelo mediante su digest (o usa 'colab-activo:latest').
    2. Si el modelo configurado en VISION_MODEL está disponible en el servidor, lo utiliza.
    3. Si hay otros modelos descargados en el servidor (ej. usuario descargó otro modelo en Colab),
       selecciona el más reciente.
    4. Si no se puede consultar /api/tags, usa el fallback configurado en VISION_MODEL.
    """
    host = (ollama_host or obtener_ollama_host()).rstrip("/")
    fallback_model = obtener_modelo_configurado()

    try:
        response = requests.get(
            f"{host}/api/tags",
            headers=OLLAMA_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        models = response.json().get("models", [])
        if not isinstance(models, list) or not models:
            return fallback_model

        # 1. Buscar alias 'colab-activo' configurado desde Google Colab
        colab_entry = next(
            (
                m for m in models
                if isinstance(m, dict)
                and str(m.get("name", "")).split(":")[0] == COLAB_ACTIVE_ALIAS
            ),
            None,
        )
        if colab_entry is not None:
            target_digest = colab_entry.get("digest")
            if target_digest:
                real_model = next(
                    (
                        m["name"] for m in models
                        if isinstance(m, dict)
                        and m.get("digest") == target_digest
                        and str(m.get("name", "")).split(":")[0] != COLAB_ACTIVE_ALIAS
                    ),
                    None,
                )
                if real_model:
                    logger.info(f"Modelo seleccionado en Google Colab detectado: {real_model}")
                    return real_model
            return str(colab_entry.get("name", f"{COLAB_ACTIVE_ALIAS}:latest"))

        # 2. Lista de modelos disponibles en el servidor
        disponibles = [
            m for m in models
            if isinstance(m, dict)
            and m.get("name")
            and str(m.get("name", "")).split(":")[0] != COLAB_ACTIVE_ALIAS
        ]
        nombres_disponibles = [str(m["name"]) for m in disponibles]

        if fallback_model in nombres_disponibles:
            return fallback_model

        # Coincidencia sin tag ':latest'
        for nombre in nombres_disponibles:
            if nombre.split(":")[0] == fallback_model.split(":")[0] and fallback_model.endswith(":latest"):
                return nombre

        # 3. Si el servidor tiene modelos pero no el fallback local, elegir el modificado más recientemente
        if disponibles:
            disponibles_ordenados = sorted(
                disponibles,
                key=lambda m: str(m.get("modified_at", "")),
                reverse=True,
            )
            elegido = str(disponibles_ordenados[0]["name"])
            logger.info(f"Usando modelo disponible en servidor Ollama: {elegido}")
            return elegido

    except Exception as exc:
        logger.debug(f"No se pudo consultar /api/tags en {host} ({exc}); usando modelo {fallback_model}")

    return fallback_model


# Bounding box por defecto basada en normas IRAM 4504 / ISO 7200 (cuadrante inferior derecho)
FALLBACK_BBOX_IRAM = [600, 500, 1000, 1000]

PROMPT_DETECCION_CAJETIN = """\
Detecta el cajetín, carimbo o cuadro de datos técnicos del plano.
Devuelve únicamente un JSON con la bounding box en formato [ymin, xmin, ymax, xmax] normalizado de 0 a 1000.
Por normas técnicas IRAM e ISO, el cajetín suele encontrarse en la zona inferior derecha del plano.
Ejemplo de respuesta: {"bbox_2d": [750, 700, 990, 990]}\
"""

PROMPT_EXTRACCION_CAJETIN = """\
Respondé únicamente con el objeto JSON solicitado, sin explicaciones ni razonamiento.
Analizá este recorte en alta resolución del cajetín / carimbo / rótulo de datos técnicos del plano histórico y respondé en español basándote solo en lo visible.

Completá estos campos:
- texto_extraido: transcripción fiel y completa de todo el texto legible visible en este cajetín (rótulos, firmas, sellos, datos catastrales, fechas, notas y escalas).
- arquitecto: autor o proyectista (arquitecto, ingeniero o profesional firmante), sin el título profesional.
- anio: año del plano o proyecto como número de cuatro dígitos (ej. 1936).
- titulo: obra, edificio, proyecto o descripción de la vista.
- ubicacion: datos de ubicación o catastrales (ciudad, dirección, circunscripción, sección, manzana, parcela).
- escala: escala indicada en el rótulo (ej. 1:100, 1:50).
- tipo_de_plano: planta, corte, fachada, relevamiento, detalle, etc.
- material_soporte: solo si aparece escrito en el plano, no lo deduzcas.
- notas: números de expediente, sellos municipales, aprobaciones o datos técnicos que no encajen en otro campo.

Transcribí fielmente. No inventes ni corrijas datos. Usá null si un dato no aparece o es ilegible. Devolvé JSON válido y ningún texto fuera del JSON.\
"""


class CajetinBBoxSchema(BaseModel):
    bbox_2d: List[int] = Field(
        description="Bounding box del cajetín [ymin, xmin, ymax, xmax] normalizado de 0 a 1000."
    )


def _verificar_respuesta_ollama(response: requests.Response, host: str, modelo: str) -> None:
    """Valida el estado HTTP de Ollama / Ngrok y lanza errores descriptivos en caso de fallo."""
    if response.status_code == 404:
        texto = getattr(response, "text", "") or ""
        if "ngrok" in texto.lower() or "<!doctype html" in texto.lower():
            raise ExtraccionError(
                f"El túnel de Ngrok ({host}) está inactivo o desconectado. "
                "Verificá que el notebook ollama_colab.ipynb esté en ejecución en Google Colab."
            )
        try:
            err_msg = response.json().get("error", "")
        except Exception:
            err_msg = ""
        if "model" in err_msg.lower() and "not found" in err_msg.lower():
            raise ExtraccionError(
                f"El modelo '{modelo}' no está descargado en Ollama ({host}). "
                "Seleccioná y activá el modelo desde la Celda 1 de ollama_colab.ipynb en Google Colab."
            )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        detalle = ""
        try:
            err_json = response.json().get("error")
            if err_json:
                detalle = f" - Detalle Ollama: {err_json}"
        except Exception:
            pass
        raise ExtraccionError(f"No se pudo contactar a Ollama ({host}): {exc}{detalle}") from exc


def _validar_bbox(bbox: object) -> Optional[List[int]]:
    """Valida y ajusta coordenadas normalizadas [ymin, xmin, ymax, xmax] entre 0 y 1000."""
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None
    try:
        ymin, xmin, ymax, xmax = [int(v) for v in bbox]
    except (ValueError, TypeError):
        return None

    ymin = max(0, min(1000, ymin))
    xmin = max(0, min(1000, xmin))
    ymax = max(0, min(1000, ymax))
    xmax = max(0, min(1000, xmax))

    if ymax <= ymin or xmax <= xmin:
        return None

    # Descartar bboxes de tamaño infinitesimal (error de detección)
    if (ymax - ymin) < 30 or (xmax - xmin) < 30:
        return None

    return [ymin, xmin, ymax, xmax]


def _normalizar_coords_raw(
    coords: object, image_size: Optional[Tuple[int, int]] = None
) -> Optional[List[int]]:
    """Convierte coordenadas crudas a [ymin, xmin, ymax, xmax] normalizadas (0..1000).

    Soporta tanto [ymin, xmin, ymax, xmax] ya normalizadas (0..1000) como la salida
    nativa de Qwen2.5-VL en píxeles [xmin, ymin, xmax, ymax] sobre las dimensiones de la imagen.
    """
    if not isinstance(coords, (list, tuple)) or len(coords) != 4:
        return None
    try:
        vals = [int(v) for v in coords]
    except (ValueError, TypeError):
        return None

    # Si alguna coordenada supera 1000 y conocemos el tamaño (width, height),
    # el modelo devolvió píxeles reales en formato [xmin, ymin, xmax, ymax] (estándar Qwen2.5-VL)
    if image_size and image_size[0] > 0 and image_size[1] > 0 and any(v > 1000 for v in vals):
        det_w, det_h = image_size
        xmin, ymin, xmax, ymax = vals
        vals = [
            int(round(ymin * 1000 / det_h)),
            int(round(xmin * 1000 / det_w)),
            int(round(ymax * 1000 / det_h)),
            int(round(xmax * 1000 / det_w)),
        ]

    return _validar_bbox(vals)


def _extraer_bbox_de_texto(
    contenido: str, image_size: Optional[Tuple[int, int]] = None
) -> Optional[List[int]]:
    if not contenido:
        return None
    try:
        parsed = json.loads(contenido)
        if isinstance(parsed, dict) and "bbox_2d" in parsed:
            valida = _normalizar_coords_raw(parsed["bbox_2d"], image_size=image_size)
            if valida:
                return valida
        elif isinstance(parsed, list):
            valida = _normalizar_coords_raw(parsed, image_size=image_size)
            if valida:
                return valida
    except (json.JSONDecodeError, ValueError):
        pass

    match = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", contenido)
    if match:
        coords = [int(match.group(i)) for i in range(1, 5)]
        valida = _normalizar_coords_raw(coords, image_size=image_size)
        if valida:
            return valida

    return None


def detectar_cajetin_bbox(image_bytes: bytes, model: Optional[str] = None) -> List[int]:
    """Paso 1: Detecta las coordenadas del cajetín [ymin, xmin, ymax, xmax] normalizadas de 0 a 1000."""
    host = obtener_ollama_host()
    timeout = obtener_ollama_timeout()
    modelo = model or obtener_modelo_activo(host)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    image_size: Optional[Tuple[int, int]] = None
    try:
        with Image.open(io.BytesIO(image_bytes)) as img_obj:
            image_size = img_obj.size
    except Exception:
        image_size = None

    payload = {
        "model": modelo,
        "messages": [
            {
                "role": "user",
                "content": PROMPT_DETECCION_CAJETIN,
                "images": [image_b64],
            }
        ],
        "format": CajetinBBoxSchema.model_json_schema(),
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 512},
    }

    try:
        response = requests.post(
            f"{host}/api/chat", json=payload, headers=OLLAMA_HEADERS, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        contenido = data.get("message", {}).get("content", "")
        bbox = _extraer_bbox_de_texto(contenido, image_size=image_size)
        if bbox:
            logger.info(f"Cajetín detectado con éxito ({modelo}): {bbox}")
            return bbox
    except Exception as exc:
        logger.warning(f"Fallo en detección automática de cajetín: {exc}")

    logger.info(f"Usando coordenadas de cajetín por norma técnica IRAM: {FALLBACK_BBOX_IRAM}")
    return FALLBACK_BBOX_IRAM


def extraer_datos_cajetin(cajetin_bytes: bytes, model: Optional[str] = None) -> PlanoHistorico:
    """Paso 2: Extrae los datos técnicos directamente del recorte en alta resolución."""
    host = obtener_ollama_host()
    timeout = obtener_ollama_timeout()
    modelo = model or obtener_modelo_activo(host)
    _ultima_corrida.modelo = modelo
    _ultima_corrida.version_prompt = VERSION_PROMPT
    image_b64 = base64.b64encode(cajetin_bytes).decode("utf-8")

    payload = {
        "model": modelo,
        "messages": [
            {
                "role": "user",
                "content": PROMPT_EXTRACCION_CAJETIN,
                "images": [image_b64],
            }
        ],
        "format": PlanoHistorico.model_json_schema(),
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 8192},
    }

    try:
        response = requests.post(
            f"{host}/api/chat", json=payload, headers=OLLAMA_HEADERS, timeout=timeout
        )
        _verificar_respuesta_ollama(response, host, modelo)
    except ExtraccionError:
        raise
    except requests.RequestException as exc:
        raise ExtraccionError(f"No se pudo contactar a Ollama: {exc}") from exc

    data = response.json()
    mensaje = data.get("message", {})
    contenido = mensaje.get("content", "")
    _ultima_corrida.json_crudo = contenido or None

    if not contenido:
        payload["messages"][0]["content"] = (
            "Analizá la imagen del cajetín y devolvé SOLO un objeto JSON válido con los campos "
            "del esquema. Usá null cuando un dato no sea visible."
        )
        try:
            response = requests.post(
                f"{host}/api/chat", json=payload, headers=OLLAMA_HEADERS, timeout=timeout
            )
            _verificar_respuesta_ollama(response, host, modelo)
        except ExtraccionError:
            raise
        except requests.RequestException as exc:
            raise ExtraccionError(f"No se pudo contactar a Ollama: {exc}") from exc
        data = response.json()
        mensaje = data.get("message", {})
        contenido = mensaje.get("content", "")
        _ultima_corrida.json_crudo = contenido or None

    try:
        if not contenido:
            raise ExtraccionError(
                "El modelo no devolvió un JSON válido: contenido vacío"
                + ("; la respuesta quedó en thinking" if mensaje.get("thinking") else "")
            )
        parsed = json.loads(contenido)
        if isinstance(parsed, dict) and "texto extraido" in parsed and "texto_extraido" not in parsed:
            parsed["texto_extraido"] = parsed.pop("texto extraido")
        return PlanoHistorico.model_validate(parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ExtraccionError(
            f"El modelo no devolvió un JSON válido: {contenido!r}"
        ) from exc


def extraer_datos_plano(
    image_bytes: bytes, output_cajetin_path: Optional[str] = None
) -> PlanoHistorico:
    """Pipeline completo en 2 pasos:

    1. Detecta la bounding box del cajetín con el modelo de visión activo.
    2. Recorta el cajetín de la imagen original en alta resolución.
    3. Extrae la información técnica del recorte con JSON estructurado.
    """
    host = obtener_ollama_host()
    modelo = obtener_modelo_activo(host)
    _ultima_corrida.modelo = modelo
    _ultima_corrida.version_prompt = VERSION_PROMPT
    logger.info(f"Iniciando detección del cajetín en {host} con modelo '{modelo}'...")
    # Preprocesar versión ligera para no saturar memoria durante la detección geométrica
    imagen_deteccion = preprocess_image(image_bytes)
    bbox = detectar_cajetin_bbox(imagen_deteccion, model=modelo)

    logger.info(f"Recortando cajetín en alta resolución usando bbox {bbox}...")
    cajetin_img = crop_cajetin_from_bbox(
        image_bytes, bbox, output_path=output_cajetin_path
    )
    cajetin_hd_bytes = preprocess_cajetin(cajetin_img)

    logger.info(f"Extrayendo datos estructurados desde el recorte del cajetín con '{modelo}'...")
    try:
        return extraer_datos_cajetin(cajetin_hd_bytes, model=modelo)
    except ExtraccionError as exc:
        logger.warning(
            f"Extracción sobre el recorte falló ({exc}), reintentando con plano completo..."
        )
        return extraer_datos_cajetin(imagen_deteccion, model=modelo)
