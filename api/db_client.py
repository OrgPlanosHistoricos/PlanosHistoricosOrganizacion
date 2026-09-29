"""Cliente de MongoDB: expone la colección donde se insertan las extracciones."""
import os

from pymongo import MongoClient

MONGODB_URI = os.environ["MONGODB_URI"]

_client = MongoClient(MONGODB_URI)
_db = _client["planos_db"]
coleccion_extracciones = _db["extracciones"]
