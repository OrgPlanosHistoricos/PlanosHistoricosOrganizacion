from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db_client import coleccion_extracciones
from .preprocessing import preprocess_image
from .schemas import ArchivoInfo, DocumentoExtraccion
from .storage_client import subir_plano
from .vision_client import ExtraccionError, extraer_datos_plano

app = FastAPI(
    title="API de Reconocimiento de Planos Históricos",
    description="Sube un plano escaneado y recibí los datos extraídos en JSON.",
    version="1.0.0",
)

# El front se sirve en un origen distinto (nginx en :8080) a la API (:8000),
# así que el navegador bloquea las llamadas sin estos headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FORMATOS_VALIDOS = {"image/jpeg", "image/png", "image/webp", "image/tiff"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/procesar-plano")
async def procesar_plano(archivo: UploadFile = File(...)):
    if archivo.content_type not in FORMATOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {archivo.content_type}. "
            f"Usá {', '.join(FORMATOS_VALIDOS)}.",
        )

    contenido = await archivo.read()

    supabase_url = subir_plano(contenido, archivo.filename, archivo.content_type)
    imagen_procesada = preprocess_image(contenido)

    # Un reintento simple: los VLM chicos a veces fallan la primera vez
    extraccion = None
    ultimo_error = None
    for intento in range(2):
        try:
            extraccion = extraer_datos_plano(imagen_procesada)
            break
        except ExtraccionError as exc:
            ultimo_error = exc

    if extraccion is None:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo extraer la información del plano: {ultimo_error}",
        )

    documento = DocumentoExtraccion(
        archivo=ArchivoInfo(nombre_original=archivo.filename, supabase_url=supabase_url),
        extraccion_qwen=extraccion,
    )

    coleccion_extracciones.insert_one(documento.model_dump())
    return JSONResponse(content=documento.model_dump(mode="json"))
