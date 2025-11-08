from pydantic import BaseModel, Field
from typing import Optional


class ItineraryRequest(BaseModel):
    destination_id: int = Field(..., gt=0, description="ID del destino (servicio_id de un hotel)")
    hotel_id: int = Field(..., gt=0, description="ID del hotel (servicio_id)")
    dias: int = Field(..., ge=1, le=15, description="Número de días del itinerario (1-15)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "destination_id": 1,
                "hotel_id": 1,
                "dias": 2
            }
        }
