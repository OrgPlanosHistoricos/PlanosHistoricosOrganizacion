"""Cliente de Supabase Storage: sube el archivo original y devuelve su URL pública."""
import os
import uuid

from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BUCKET_NAME = "planos_escaneados"

_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def subir_plano(contenido: bytes, nombre_original: str, content_type: str) -> str:
    extension = nombre_original.rsplit(".", 1)[-1] if "." in nombre_original else "bin"
    nombre_storage = f"{uuid.uuid4()}.{extension}"

    _client.storage.from_(BUCKET_NAME).upload(
        nombre_storage, contenido, {"content-type": content_type}
    )
    return _client.storage.from_(BUCKET_NAME).get_public_url(nombre_storage)
