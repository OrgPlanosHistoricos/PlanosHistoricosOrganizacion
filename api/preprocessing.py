"""
Preprocesamiento simple de imágenes de planos históricos.
Planos viejos suelen venir con bajo contraste, manchas o tamaños
grandes que no aportan nada al modelo. Esto mejora la extracción
sin necesitar nada más pesado que Pillow.
Preprocesamiento de planos históricos: imágenes y PDFs.

Flujo:
  - PDF  → rasteriza la primera página con PyMuPDF a 150 DPI y la pasa
            como imagen JPEG al pipeline de mejora habitual.
  - Imagen → redimensiona, autocontraste y realce de nitidez con Pillow.

El resultado siempre es JPEG en bytes, listo para ser codificado en base64
y enviado al modelo de visión.
"""
import io
from PIL import Image, ImageOps, ImageEnhance

MAX_DIMENSION = 1600  # el modelo de visión no necesita más resolución que esta
MAX_DIMENSION = 1200  # resolución máxima; 1200 px equilibra detalle e inferencia
PDF_DPI = 150         # DPI de rasterización del PDF (150 = buena legibilidad sin exceso)


def preprocess_image(image_bytes: bytes) -> bytes:
def _rasterize_pdf_first_page(pdf_bytes: bytes) -> bytes:
    """Convierte la primera página de un PDF en JPEG usando PyMuPDF."""
    import fitz  # importación diferida para no romper el arranque si falta el paquete

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise ValueError("El PDF no tiene páginas.")

    page = doc[0]
    # Escala: 1 punto PDF = 1/72 pulgada; escala = DPI / 72
    mat = fitz.Matrix(PDF_DPI / 72, PDF_DPI / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

    # Convertir a bytes JPEG vía Pillow para unificar el pipeline
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=90)
    return output.getvalue()


def preprocess_image(image_bytes: bytes, content_type: str = "image/jpeg") -> bytes:
    """
    Preprocesa un plano para enviarlo al modelo de visión.

    Parámetros
    ----------
    image_bytes : bytes
        Contenido crudo del archivo subido.
    content_type : str
        MIME type del archivo.  Si es "application/pdf" se rasteriza
        la primera página antes de aplicar el pipeline de imagen.
    """
    if content_type == "application/pdf":
        image_bytes = _rasterize_pdf_first_page(image_bytes)

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
