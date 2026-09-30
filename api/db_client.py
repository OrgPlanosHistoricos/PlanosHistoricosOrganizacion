"""Cliente de MongoDB: expone la colección donde se insertan las extracciones."""
import logging
import os
from typing import Optional

from pymongo import MongoClient

logger = logging.getLogger("planos.db")

MONGODB_URI = os.environ.get("MONGODB_URI", "")

_client: Optional[MongoClient] = None
coleccion_extracciones = None

if MONGODB_URI:
    try:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db = _client["planos_db"]
        coleccion_extracciones = _db["extracciones"]
    except Exception as e:
        logger.error(f"Error al inicializar cliente de MongoDB: {e}")
        coleccion_extracciones = None
