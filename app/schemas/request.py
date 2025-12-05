from pydantic import BaseModel, Field, field_validator
from datetime import date
from enum import Enum


class InteresEnum(str, Enum):
    """Tipos de interés de viaje disponibles"""
    AVENTURA = "Aventura"
    RELAJACION = "Relajación"
    CULTURA = "Cultura"
    GASTRONOMIA = "Gastronomía"


class ItineraryRequest(BaseModel):
    destino: str = Field(..., min_length=2, max_length=100, description="Nombre de la ciudad destino")
    hotel_id: int = Field(..., gt=0, description="ID del hotel (servicio_id)")
    fecha_checkin: date = Field(..., description="Fecha de check-in en el hotel")
    fecha_checkout: date = Field(..., description="Fecha de check-out del hotel")
    interes: InteresEnum = Field(..., description="Tipo de interés de viaje (obligatorio)")
    
    @field_validator('fecha_checkout')
    @classmethod
    def validar_fechas(cls, v, info):
        """Valida que checkout sea posterior a checkin"""
        if 'fecha_checkin' in info.data:
            fecha_checkin = info.data['fecha_checkin']
            if v <= fecha_checkin:
                raise ValueError('La fecha de check-out debe ser posterior a la fecha de check-in')
            
            # Calcular días y validar rango
            dias = (v - fecha_checkin).days
            if dias < 1 or dias > 15:
                raise ValueError('La duración del viaje debe estar entre 1 y 15 días')
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "destino": "Lima",
                "hotel_id": 1,
                "fecha_checkin": "2025-12-01",
                "fecha_checkout": "2025-12-04",
                "interes": "Cultura"
            }
        }
