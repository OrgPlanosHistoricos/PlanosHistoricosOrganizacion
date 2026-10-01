"""Cliente de MinIO: guarda y lee los archivos originales de los planos."""
import io
import os
import uuid

from minio import Minio

BUCKET = os.environ.get("MINIO_BUCKET", "planos")

_client = Minio(
    os.environ["MINIO_ENDPOINT"],
    access_key=os.environ["MINIO_ACCESS_KEY"],
    secret_key=os.environ["MINIO_SECRET_KEY"],
    secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
)

_bucket_listo = False


def _asegurar_bucket() -> None:
    global _bucket_listo
    if _bucket_listo:
        return
    if not _client.bucket_exists(BUCKET):
        _client.make_bucket(BUCKET)
    _bucket_listo = True


def subir_archivo(contenido: bytes, nombre_original: str, content_type: str) -> str:
    """Sube el archivo y devuelve su key dentro del bucket."""
    _asegurar_bucket()
    extension = nombre_original.rsplit(".", 1)[-1] if "." in nombre_original else "bin"
    key = f"{uuid.uuid4()}.{extension}"
    _client.put_object(
        BUCKET, key, io.BytesIO(contenido), length=len(contenido), content_type=content_type
    )
    return key


def obtener_archivo(key: str) -> bytes:
    respuesta = _client.get_object(BUCKET, key)
    try:
        return respuesta.read()
    finally:
        respuesta.close()
        respuesta.release_conn()


def borrar_archivo(key: str) -> bool:
    """Elimina el archivo del bucket si existe."""
    try:
        _client.remove_object(BUCKET, key)
        return True
    except Exception:
        return False


def check_minio_health() -> bool:
    """Verifica si MinIO responde y el bucket existe."""
    try:
        _asegurar_bucket()
        return _client.bucket_exists(BUCKET)
    except Exception:
        return False

