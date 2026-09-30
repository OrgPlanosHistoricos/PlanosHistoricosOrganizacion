import logging
import os
from typing import Optional
import uuid

from supabase import create_client, Client

logger = logging.getLogger("planos.storage")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BUCKET_NAME = "planos_escaneados"

_client: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        logger.warning(f"No se pudo inicializar cliente de Supabase: {exc}")


def subir_plano(contenido: bytes, nombre_original: str, content_type: str) -> str:
    if not _client:
        raise RuntimeError("Supabase no está configurado (faltan SUPABASE_URL y/o SUPABASE_KEY).")
    extension = nombre_original.rsplit(".", 1)[-1] if "." in nombre_original else "bin"
    nombre_storage = f"{uuid.uuid4()}.{extension}"

    _client.storage.from_(BUCKET_NAME).upload(
        nombre_storage, contenido, {"content-type": content_type}
    )
    return _client.storage.from_(BUCKET_NAME).get_public_url(nombre_storage)
