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
MODEL_NAME = os.environ.get("VISION_MODEL", "qwen2.5vl:3b")

PROMPT = (
    "Sos un asistente que analiza planos arquitectónicos históricos "
    "escaneados. Observá la imagen con atención (títulos, cartelas, "
    "sellos, textos manuscritos o impresos) y completá los datos que "
    "puedas identificar con certeza. Si un dato no aparece en la "
    "imagen, dejalo en null - no inventes información."
)


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
        "options": {"temperature": 0.1},
    }

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat", json=payload, timeout=120
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExtraccionError(f"No se pudo contactar a Ollama: {exc}") from exc

    data = response.json()
    contenido = data.get("message", {}).get("content", "")

    try:
        parsed = json.loads(contenido)
        return PlanoHistorico.model_validate(parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ExtraccionError(
            f"El modelo no devolvió un JSON válido: {contenido!r}"
        ) from exc
