"""
Preprocesamiento simple de imágenes de planos históricos.
Planos viejos suelen venir con bajo contraste, manchas o tamaños
grandes que no aportan nada al modelo. Esto mejora la extracción
sin necesitar nada más pesado que Pillow.
"""
import io
from PIL import Image, ImageOps, ImageEnhance

MAX_DIMENSION = 1600  # el modelo de visión no necesita más resolución que esta


def preprocess_image(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")

    # Redimensionar si es muy grande (ahorra tiempo de inferencia)
    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    # Autocontraste suave, útil para planos escaneados con poco contraste
    image = ImageOps.autocontrast(image, cutoff=1)

    # Un poco más de nitidez ayuda a leer texto pequeño (títulos, firmas)
    sharpener = ImageEnhance.Sharpness(image)
    image = sharpener.enhance(1.5)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()
