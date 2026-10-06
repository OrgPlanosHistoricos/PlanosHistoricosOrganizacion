"""
Preprocesamiento y recorte de imágenes de planos históricos.
Permite optimizar imágenes completas para inferencia rápida y realizar
el recorte (crop) en alta resolución del cajetín técnico según coordenadas normalizadas.
"""
import io
import logging
from typing import List, Optional, Union
from PIL import Image, ImageOps, ImageEnhance
import pypdfium2 as pdfium

logger = logging.getLogger("planos.preprocessing")

MAX_DIMENSION = 1600  # Resolución para análisis preliminar o planos completos
MAX_CAJETIN_DIMENSION = 1800  # Resolución máxima para el recorte del cajetín


def pdf_to_image(pdf_input: Union[bytes, bytearray], page_index: int = 0) -> Image.Image:
    """Convierte una página de un archivo PDF a PIL.Image en alta resolución."""
    pdf = pdfium.PdfDocument(pdf_input)
    if len(pdf) == 0:
        raise ValueError("El documento PDF no contiene páginas.")
    if page_index >= len(pdf) or page_index < 0:
        page_index = 0
    page = pdf[page_index]
    width, height = page.get_size()
    max_side = max(width, height)
    # Escala dinámica para asegurar legibilidad (~2400-3000px en el lado mayor, min 1.5x, max 4.0x)
    scale = max(1.5, min(4.0, 2600.0 / max(max_side, 1)))
    bitmap = page.render(scale=scale)
    img = bitmap.to_pil()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def pdf_page_to_jpeg_bytes(
    pdf_bytes: Union[bytes, bytearray], page_index: int = 0, quality: int = 92
) -> bytes:
    """Renderiza una página de un PDF como imagen JPEG en bytes."""
    img = pdf_to_image(pdf_bytes, page_index=page_index)
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality)
    return output.getvalue()


def crop_cajetin_from_bbox(
    image_input: Union[str, bytes, Image.Image],
    bbox: List[int],
    output_path: Optional[str] = None,
    padding_pct: float = 0.02,
) -> Image.Image:
    """Recorta el cajetín de un plano usando una bounding box [ymin, xmin, ymax, xmax] normalizada de 0 a 1000.
    
    Acepta una ruta de archivo (str), bytes en memoria o una instancia PIL.Image.
    Si se proporciona output_path, guarda el recorte en el archivo especificado.
    Añade un margen de seguridad (padding_pct) para evitar recortar bordes de texto.
    """
    if isinstance(image_input, (bytes, bytearray)) and image_input.startswith(b"%PDF"):
        img = pdf_to_image(image_input, page_index=0)
    elif isinstance(image_input, str):
        if image_input.lower().endswith(".pdf"):
            with open(image_input, "rb") as f:
                img = pdf_to_image(f.read(), page_index=0)
        else:
            img = Image.open(image_input)
    elif isinstance(image_input, (bytes, bytearray)):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, Image.Image):
        img = image_input
    else:
        raise ValueError("image_input debe ser ruta (str), bytes o PIL.Image")

    if img.mode != "RGB":
        img = img.convert("RGB")

    width, height = img.size
    ymin, xmin, ymax, xmax = bbox

    # Desnormalizar coordenadas a píxeles reales
    left = int((xmin / 1000) * width)
    top = int((ymin / 1000) * height)
    right = int((xmax / 1000) * width)
    bottom = int((ymax / 1000) * height)

    # Margen de seguridad para no cortar rótulos o texto en los límites
    pad_x = int(padding_pct * width)
    pad_y = int(padding_pct * height)

    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(width, right + pad_x)
    bottom = min(height, bottom + pad_y)

    # Validar dimensiones mínimas
    if right <= left or bottom <= top:
        logger.warning(
            f"Bbox inválida tras desnormalizar ({left}, {top}, {right}, {bottom}), usando cuadrante inferior derecho."
        )
        left = int(width * 0.5)
        top = int(height * 0.6)
        right = width
        bottom = height

    cajetin_crop = img.crop((left, top, right, bottom))

    if output_path:
        cajetin_crop.save(output_path)
        logger.info(f"Cajetín guardado en {output_path}")

    return cajetin_crop


def preprocess_cajetin(cajetin_input: Union[Image.Image, bytes]) -> bytes:
    """Aplica mejoras de contraste y nitidez al recorte del cajetín en alta resolución."""
    if isinstance(cajetin_input, (bytes, bytearray)):
        image = Image.open(io.BytesIO(cajetin_input))
    else:
        image = cajetin_input

    if image.mode != "RGB":
        image = image.convert("RGB")

    # Redimensionar solo si el recorte es excesivamente grande
    if max(image.size) > MAX_CAJETIN_DIMENSION:
        image.thumbnail((MAX_CAJETIN_DIMENSION, MAX_CAJETIN_DIMENSION), Image.LANCZOS)

    # Autocontraste para resaltar tinta, sellos y lápiz
    image = ImageOps.autocontrast(image, cutoff=1)

    # Nitidez para mejorar legibilidad de tipografía y números de catastro/escala
    sharpener = ImageEnhance.Sharpness(image)
    image = sharpener.enhance(1.5)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    return output.getvalue()


def preprocess_image(image_bytes: bytes) -> bytes:
    """Preprocesamiento general para planos completos (análisis o inferencia rápida)."""
    if image_bytes.startswith(b"%PDF"):
        image = pdf_to_image(image_bytes, page_index=0)
    else:
        image = Image.open(io.BytesIO(image_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Redimensionar si es muy grande (ahorra tiempo de inferencia)
    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    # Autocontraste suave
    image = ImageOps.autocontrast(image, cutoff=1)

    # Nitidez
    sharpener = ImageEnhance.Sharpness(image)
    image = sharpener.enhance(1.5)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()

