from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .preprocessing import preprocess_image
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
    imagen_procesada = preprocess_image(contenido)

    # Un reintento simple: los VLM chicos a veces fallan la primera vez
    ultimo_error = None
    for intento in range(2):
        try:
            resultado = extraer_datos_plano(imagen_procesada)
            return JSONResponse(content=resultado.model_dump())
        except ExtraccionError as exc:
            ultimo_error = exc

    raise HTTPException(
        status_code=502,
        detail=f"No se pudo extraer la información del plano: {ultimo_error}",
    )
