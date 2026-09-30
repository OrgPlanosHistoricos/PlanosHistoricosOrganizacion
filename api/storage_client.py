"""Cliente de Supabase Storage: sube el archivo original y devuelve su URL pública."""
import logging
import os
import uuid
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger("planos.storage")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BUCKET_NAME = "planos_escaneados"

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


def subir_plano(contenido: bytes, nombre_original: str, content_type: str) -> str:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Cliente de Supabase no disponible (verifique SUPABASE_KEY y SUPABASE_URL)")

    extension = nombre_original.rsplit(".", 1)[-1] if "." in nombre_original else "bin"
    nombre_storage = f"{uuid.uuid4()}.{extension}"

    client.storage.from_(BUCKET_NAME).upload(
        nombre_storage, contenido, {"content-type": content_type}
    )
    return client.storage.from_(BUCKET_NAME).get_public_url(nombre_storage)
