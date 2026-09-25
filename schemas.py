"""
Esquema de los datos que queremos extraer de cada plano histórico.
Agregá o quitá campos según lo que necesites - el modelo de visión
va a usar este mismo esquema para saber qué generar.
"""
from typing import Optional
from pydantic import BaseModel, Field


class PlanoHistorico(BaseModel):
    arquitecto: Optional[str] = Field(
        None, description="Nombre del arquitecto o autor del plano, si figura"
    )
    anio: Optional[int] = Field(
        None, description="Año de realización del plano o de la construcción"
    )
    titulo: Optional[str] = Field(
        None, description="Título o nombre de la obra/edificio representado"
    )
    ubicacion: Optional[str] = Field(
        None, description="Ciudad, dirección o ubicación mencionada en el plano"
    )
    escala: Optional[str] = Field(
        None, description="Escala del plano, ej. '1:100'"
    )
    tipo_de_plano: Optional[str] = Field(
        None, description="Tipo de plano: planta, corte, fachada, detalle, etc."
    )
    material_soporte: Optional[str] = Field(
        None, description="Material sobre el que está dibujado, si se menciona (papel, tela, calco, etc.)"
    )
    notas: Optional[str] = Field(
        None, description="Cualquier otro texto o dato relevante visible en el plano"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "arquitecto": "Francisco Salamone",
                "anio": 1936,
                "titulo": "Palacio Municipal de Azul",
                "ubicacion": "Azul, Buenos Aires",
                "escala": "1:50",
                "tipo_de_plano": "fachada principal",
                "material_soporte": "papel tela",
                "notas": "Sello del archivo municipal en la esquina inferior derecha",
            }
        }
