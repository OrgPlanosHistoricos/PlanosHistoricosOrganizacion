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
    "Analizá este plano arquitectónico histórico escaneado y extraé sus "
    "metadatos. El papel puede estar envejecido, manchado o con tinta "
    "desvaída, y el texto puede ser impreso o manuscrito.\n\n"
    "Cómo trabajar:\n"
    "1. Empezá por la cartela o rótulo del plano (normalmente en una esquina "
    "o borde), los sellos y las firmas: ahí está la mayor parte de los datos. "
    "Después revisá el resto de la hoja.\n"
    "2. Transcribí lo que efectivamente se lee. No completes ni corrijas "
    "nombres o fechas de memoria.\n"
    "3. Cada dato va en el campo que le corresponde según la descripción de "
    "ese campo. Antes de ubicar algo en 'notas', comprobá si encaja en otro "
    "campo: 'notas' es el último recurso.\n"
    "4. Si un dato no aparece o no se lee con certeza, dejá el campo en null. "
    "Es mejor null que un dato dudoso."
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
            f"{OLLAMA_HOST}/api/chat", json=payload, timeout=300
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
