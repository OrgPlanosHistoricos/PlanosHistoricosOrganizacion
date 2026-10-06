"""
Cliente HTTP hacia Ollama con soporte para extracción en dos pasos:
1. Grounding / Detección del cajetín (carimbo/cuadro técnico) en coordenadas normalizadas [ymin, xmin, ymax, xmax].
2. Recorte del cajetín en alta resolución y extracción estructurada con JSON Schema.
"""
import base64
import json
import logging
import os
import re
from typing import List, Optional

from pydantic import BaseModel, Field
import requests

from .preprocessing import crop_cajetin_from_bbox, preprocess_cajetin, preprocess_image
from .schemas import PlanoHistorico

logger = logging.getLogger("planos.vision")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = os.environ.get("VISION_MODEL", "qwen2.5vl:3b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))

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


class ExtraccionError(Exception):
    pass


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


def _extraer_bbox_de_texto(contenido: str) -> Optional[List[int]]:
    if not contenido:
        return None
    try:
        parsed = json.loads(contenido)
        if isinstance(parsed, dict) and "bbox_2d" in parsed:
            valida = _validar_bbox(parsed["bbox_2d"])
            if valida:
                return valida
        elif isinstance(parsed, list):
            valida = _validar_bbox(parsed)
            if valida:
                return valida
    except (json.JSONDecodeError, ValueError):
        pass

    match = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", contenido)
    if match:
        coords = [int(match.group(i)) for i in range(1, 5)]
        valida = _validar_bbox(coords)
        if valida:
            return valida

    return None


def detectar_cajetin_bbox(image_bytes: bytes) -> List[int]:
    """Paso 1: Detecta las coordenadas del cajetín [ymin, xmin, ymax, xmax] normalizadas de 0 a 1000."""
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": MODEL_NAME,
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
        "options": {"temperature": 0.1, "think": False, "num_predict": 512},
    }

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        contenido = data.get("message", {}).get("content", "")
        bbox = _extraer_bbox_de_texto(contenido)
        if bbox:
            logger.info(f"Cajetín detectado con éxito: {bbox}")
            return bbox
    except Exception as exc:
        logger.warning(f"Fallo en detección automática de cajetín: {exc}")

    logger.info(f"Usando coordenadas de cajetín por norma técnica IRAM: {FALLBACK_BBOX_IRAM}")
    return FALLBACK_BBOX_IRAM


def extraer_datos_cajetin(cajetin_bytes: bytes) -> PlanoHistorico:
    """Paso 2: Extrae los datos técnicos directamente del recorte en alta resolución."""
    image_b64 = base64.b64encode(cajetin_bytes).decode("utf-8")

    payload = {
        "model": MODEL_NAME,
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
        "options": {"temperature": 0.1, "think": False, "num_predict": 8192},
    }

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExtraccionError(f"No se pudo contactar a Ollama: {exc}") from exc

    data = response.json()
    mensaje = data.get("message", {})
    contenido = mensaje.get("content", "")

    if not contenido:
        payload["messages"][0]["content"] = (
            "Analizá la imagen del cajetín y devolvé SOLO un objeto JSON válido con los campos "
            "del esquema. Usá null cuando un dato no sea visible."
        )
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ExtraccionError(f"No se pudo contactar a Ollama: {exc}") from exc
        data = response.json()
        mensaje = data.get("message", {})
        contenido = mensaje.get("content", "")

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
    
    1. Detecta la bounding box del cajetín con Qwen2.5-VL.
    2. Recorta el cajetín de la imagen original en alta resolución.
    3. Extrae la información técnica del recorte con JSON estructurado.
    """
    logger.info("Iniciando detección del cajetín en el plano...")
    # Preprocesar versión ligera para no saturar memoria durante la detección geométrica
    imagen_deteccion = preprocess_image(image_bytes)
    bbox = detectar_cajetin_bbox(imagen_deteccion)

    logger.info(f"Recortando cajetín en alta resolución usando bbox {bbox}...")
    cajetin_img = crop_cajetin_from_bbox(
        image_bytes, bbox, output_path=output_cajetin_path
    )
    cajetin_hd_bytes = preprocess_cajetin(cajetin_img)

    logger.info("Extrayendo datos estructurados desde el recorte del cajetín...")
    try:
        return extraer_datos_cajetin(cajetin_hd_bytes)
    except ExtraccionError as exc:
        logger.warning(
            f"Extracción sobre el recorte falló ({exc}), reintentando con plano completo..."
        )
        return extraer_datos_cajetin(imagen_deteccion)

