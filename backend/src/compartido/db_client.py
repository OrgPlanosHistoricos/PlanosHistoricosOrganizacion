"""Cliente de MongoDB: expone las colecciones de extracciones y corridas de IA."""
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

logger = logging.getLogger("planos.db")

MONGODB_URI = os.environ.get("MONGODB_URI", "")

_client: Optional[MongoClient] = None
coleccion_extracciones = None
coleccion_corridas_ia = None

if MONGODB_URI:
    try:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db = _client["planos_db"]
        coleccion_extracciones = _db["extracciones"]
        coleccion_corridas_ia = _db["corridas_ia"]
    except Exception as e:
        logger.error(f"Error al inicializar cliente de MongoDB: {e}")
        coleccion_extracciones = None
        coleccion_corridas_ia = None
