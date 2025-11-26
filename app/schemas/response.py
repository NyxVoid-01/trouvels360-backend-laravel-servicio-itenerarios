from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal


class UbicacionSchema(BaseModel):
    lat: float
    lon: float


class ActividadSchema(BaseModel):
    tour_id: int
    nombre: str
    descripcion: Optional[str]
    duracion_horas: float
    precio: Decimal
    moneda: str = "PEN"
    promedio_estrellas: float
    total_resenas: int
    imagen_url: Optional[str]
    ubicacion: UbicacionSchema
    distancia_km: float = Field(..., description="Distancia en km desde el hotel")
    score: float = Field(..., description="Score de calidad ponderado (0-100)")


class DiaItinerarioSchema(BaseModel):
    dia: int
    fecha_sugerida: Optional[str] = None
    actividades: List[ActividadSchema]
    horas_totales: float
    costo_total_dia: Decimal
    distancia_total_dia: float = Field(..., description="Distancia total recorrida en el día (km)")


class DestinoSchema(BaseModel):
    nombre: str
    ciudad: str
    pais: str


class HotelSchema(BaseModel):
    id: int
    nombre: str
    direccion: str
    estrellas: Optional[int]


class ResumenSchema(BaseModel):
    total_dias: int
    total_tours: int
    costo_total: Decimal
    promedio_valoracion: float


class ItinerarioDataSchema(BaseModel):
    destino: DestinoSchema
    hotel: HotelSchema
    itinerario: List[DiaItinerarioSchema]
    resumen: ResumenSchema


class ItineraryResponse(BaseModel):
    success: bool = True
    data: ItinerarioDataSchema
    mensaje: str = "Para guardar este itinerario y personalizarlo, regístrate gratis"
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "destino": {
                        "id": 1,
                        "nombre": "Lima",
                        "pais": "Perú"
                    },
                    "hotel": {
                        "id": 1,
                        "nombre": "Hotel La Hacienda",
                        "direccion": "Av. Principal 123",
                        "estrellas": 4
                    },
                    "itinerario": [
                        {
                            "dia": 1,
                            "fecha_sugerida": None,
                            "actividades": [],
                            "horas_totales": 8,
                            "costo_total_dia": 120.00
                        }
                    ],
                    "resumen": {
                        "total_dias": 2,
                        "total_tours": 4,
                        "costo_total": 240.00,
                        "promedio_valoracion": 4.5
                    }
                },
                "mensaje": "Para guardar este itinerario y personalizarlo, regístrate gratis"
            }
        }


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detalles: Optional[dict] = None
