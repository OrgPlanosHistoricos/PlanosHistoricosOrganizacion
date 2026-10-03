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
Analizá este plano arquitectónico histórico escaneado y extraé sus metadatos. \
El papel puede estar envejecido, manchado o con tinta desvaída, y el texto \
puede ser impreso o manuscrito.

Instrucciones paso a paso:
1. En primer lugar, transcribí en el campo 'texto_extraido' TODO el texto legible que \
encuentres en el plano (carátula, recuadros, rótulos, firmas, sellos, \
aprobaciones, notas, leyendas, cotas, títulos, etc.). Extraé absolutamente todo el texto \
aquí antes de clasificarlo en los demás campos.
2. A continuación, leé y analizá detenidamente ese texto que acabás de transcribir \
en 'texto_extraido' y, a partir de él, andá ubicando cada dato en su campo \
correspondiente del JSON:
   - arquitecto: nombre completo del profesional autor o proyectista (sin título profesional ni rótulo).
   - anio: año del plano o proyecto (número de 4 dígitos, ej. 1936).
   - titulo: nombre de la obra, edificio, proyecto o descripción de la vista.
   - ubicacion: ciudad, dirección o ubicación mencionada en el plano.
   - escala: escala del plano (ej. '1:100', '1:50').
   - tipo_de_plano: planta, corte, fachada, detalle, etc.
   - material_soporte: material solo si está expresamente escrito en el plano (papel, tela, etc.).
   - notas: leyendas, aclaraciones o sellos relevantes que no encajen en otro campo.
3. Transcribí fielmente lo que se lee en el plano. No completes ni corrijas \
nombres o fechas de memoria ni inventes información que no esté en el plano.
4. Si un dato no figura en el texto extraído o es ilegible, su valor debe ser \
explícitamente null. Es preferible null antes que un dato dudoso.

Respondé en español y basate EXCLUSIVAMENTE en lo que ves en la imagen.\
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
        "options": {"temperature": 0.1},
    }

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExtraccionError(f"No se pudo contactar a Ollama: {exc}") from exc

    data = response.json()
    contenido = data.get("message", {}).get("content", "")

    try:
        parsed = json.loads(contenido)
        if isinstance(parsed, dict) and "texto extraido" in parsed and "texto_extraido" not in parsed:
            parsed["texto_extraido"] = parsed.pop("texto extraido")
        return PlanoHistorico.model_validate(parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ExtraccionError(
            f"El modelo no devolvió un JSON válido: {contenido!r}"
        ) from exc
