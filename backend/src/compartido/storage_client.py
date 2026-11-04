"""Cliente de Supabase Storage: guarda y lee los archivos originales de los planos y sus previsualizaciones."""
import logging
import os
import uuid
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger("planos.storage")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BUCKET_NAME = os.environ.get("SUPABASE_BUCKET", "planos_escaneados")

_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    global _client
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("SUPABASE_URL o SUPABASE_KEY no están configurados.")
        return None
    try:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _client
    except Exception as e:
        logger.error(f"Error al inicializar cliente de Supabase: {e}")
        return None


def _bucket():
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Cliente de Supabase no disponible (verifique SUPABASE_KEY y SUPABASE_URL)")
    return client.storage.from_(BUCKET_NAME)


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

