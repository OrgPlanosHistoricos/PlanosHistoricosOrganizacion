"""Cliente de Supabase Storage: guarda y lee los archivos originales de los planos y sus previsualizaciones."""
import logging
import os
from pathlib import Path
import uuid
from typing import Optional, Tuple

from dotenv import dotenv_values
from supabase import create_client, Client

logger = logging.getLogger("planos.storage")

_ENV_CANDIDATES = (
    Path(__file__).resolve().parents[2] / ".env",  # /app/.env en Docker
    Path(__file__).resolve().parents[3] / ".env",  # raíz del repo en local
)
_ENV_FILE = next((p for p in _ENV_CANDIDATES if p.is_file()), _ENV_CANDIDATES[0])


def _leer_env() -> dict:
    if _ENV_FILE.is_file():
        try:
            return {k: v for k, v in dotenv_values(_ENV_FILE).items() if v is not None}
        except Exception:
            return {}
    return {}


def _get_config() -> Tuple[str, str, str]:
    env = _leer_env()
    url = env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY", "")
    bucket = env.get("SUPABASE_BUCKET") or os.environ.get("SUPABASE_BUCKET", "planos_escaneados")
    return url, key, bucket


_client: Optional[Client] = None
_last_key: Optional[str] = None
_last_url: Optional[str] = None


def get_supabase_client() -> Optional[Client]:
    global _client, _last_key, _last_url
    url, key, _ = _get_config()
    if _client is not None and _last_key == key and _last_url == url:
        return _client
    if not url or not key:
        logger.warning("SUPABASE_URL o SUPABASE_KEY no están configurados.")
        return None
    try:
        _client = create_client(url, key)
        _last_key = key
        _last_url = url
        return _client
    except Exception as e:
        logger.error(f"Error al inicializar cliente de Supabase: {e}")
        return None


def _bucket():
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Cliente de Supabase no disponible (verifique SUPABASE_KEY y SUPABASE_URL)")
    _, _, bucket_name = _get_config()
    return client.storage.from_(bucket_name)


def subir_archivo(contenido: bytes, nombre_original: str, content_type: str) -> str:
    """Sube el archivo y devuelve su key dentro del bucket."""
    extension = nombre_original.rsplit(".", 1)[-1] if "." in nombre_original else "bin"
    return subir_archivo_con_key(contenido, f"{uuid.uuid4()}.{extension}", content_type)


def subir_archivo_con_key(contenido: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Sube un archivo con una key fija (ej. previsualizaciones), pisándolo si ya existe."""
    _bucket().upload(key, contenido, {"content-type": content_type, "upsert": "true"})
    return key


def obtener_archivo(key: str) -> bytes:
    return _bucket().download(key)


def existe_archivo(key: str) -> bool:
    """Verifica si un objeto existe en el bucket (las keys no tienen carpetas)."""
    try:
        return any(obj.get("name") == key for obj in _bucket().list("", {"search": key}))
    except Exception:
        return False


def obtener_preview_key(archivo_key: str) -> str:
    """Calcula la key correspondiente a la miniatura/preview de un archivo."""
    return f"{archivo_key}.preview.jpg"


def eliminar_archivo(key: str) -> None:
    """Eliminar es idempotente: un objeto ausente también cuenta como eliminado."""
    _bucket().remove([key])
