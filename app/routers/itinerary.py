from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.schemas.request import ItineraryRequest
from app.schemas.response import ItineraryResponse, ErrorResponse
from app.services.itinerary_service import ItineraryService
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["itinerarios"]
)


@router.post("/itinerary", response_model=ItineraryResponse, responses={
    400: {"model": ErrorResponse, "description": "Error de validación"},
    404: {"model": ErrorResponse, "description": "Recurso no encontrado"},
    503: {"model": ErrorResponse, "description": "Servicio no disponible"}
})
async def generar_itinerario(
    request: ItineraryRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un itinerario personalizado basado en el destino, hotel y número de días.
    
    - **destination_id**: ID del destino (ciudad)
    - **hotel_id**: ID del hotel seleccionado
    - **dias**: Número de días del itinerario (1-15)
    """
    try:
        service = ItineraryService(db)
        data = service.generar_itinerario(
            destination_id=request.destination_id,
            hotel_id=request.hotel_id,
            dias=request.dias
        )
        
        return ItineraryResponse(
            success=True,
            data=data,
            mensaje="Para guardar este itinerario y personalizarlo, regístrate gratis"
        )
    
    except ValueError as e:
        # Errores de validación de negocio
        error_message = str(e)
        
        if "no existe" in error_message or "no pertenece" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": error_message
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": error_message
                }
            )
    
    except Exception as e:
        # Error interno del servidor
        logger.error(f"Error generando itinerario: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "El servicio de generación de itinerarios no está disponible en este momento"
            }
        )


@router.get("/health")
async def health_check():
    """Endpoint para verificar el estado del servicio"""
    return {
        "status": "healthy",
        "service": "Itinerarios Service",
        "version": "1.0.0"
    }
