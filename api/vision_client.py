"""
Cliente HTTP hacia Ollama. Usa el parámetro "format" con el JSON Schema
de PlanoHistorico para forzar una salida estructurada (structured outputs
de Ollama) en vez de confiar en que el modelo devuelva JSON prolijo
solo por pedírselo en el prompt.
"""
import base64
import json
import os

import requests

from .schemas import PlanoHistorico

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = os.environ.get("VISION_MODEL", "qwen3-vl:4b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))

PROMPT = """\
Respondé únicamente con el objeto JSON solicitado, sin explicaciones ni razonamiento.
Analizá la imagen del plano histórico y respondé en español basándote solo en lo visible.

Completá estos campos:
- texto_extraido: transcripción de todo el texto legible (cartela, rótulos, firmas,
  sellos, notas, leyendas y cotas).
- arquitecto: autor o proyectista, sin el título profesional.
- anio: año del plano o proyecto como número de cuatro dígitos.
- titulo: obra, edificio, proyecto o descripción de la vista.
- ubicacion: ciudad, dirección o ubicación escrita.
- escala: por ejemplo, 1:100.
- tipo_de_plano: planta, corte, fachada, detalle, etc.
- material_soporte: solo si aparece escrito, no lo deduzcas de la imagen.
- notas: información relevante que no corresponda a otro campo.

Transcribí fielmente. No inventes ni corrijas datos. Usá null si un dato no aparece
o es ilegible. Devolvé JSON válido y ningún texto fuera del JSON.\
"""


class ExtraccionError(Exception):
    pass


def extraer_datos_plano(image_bytes: bytes) -> PlanoHistorico:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
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
            "Analizá la imagen y devolvé SOLO un objeto JSON válido con los campos "
            "del esquema. No expliques ni muestres razonamiento. Usá null cuando "
            "un dato no sea visible."
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
