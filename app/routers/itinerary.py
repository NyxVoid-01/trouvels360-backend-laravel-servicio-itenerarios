from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.schemas.request import ItineraryRequest
from app.schemas.response import ItineraryResponse, ErrorResponse
from app.services.itinerary_service import ItineraryService
from app.security import get_current_user, TokenData
from typing import Optional
from pydantic import ValidationError
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["itinerarios"]
)


# Dependencia opcional para autenticación
async def get_optional_current_user(
    token: Optional[str] = None
) -> Optional[TokenData]:
    """
    Autenticación opcional: retorna usuario si está autenticado, None si no.
    """
    if token:
        try:
            return await get_current_user(token)
        except:
            return None
    return None


@router.post("/itinerary", response_model=ItineraryResponse, responses={
    400: {"model": ErrorResponse, "description": "Error de validación"},
    404: {"model": ErrorResponse, "description": "Recurso no encontrado"},
    503: {"model": ErrorResponse, "description": "Servicio no disponible"}
})
async def generar_itinerario(
    request: ItineraryRequest,
    db: Session = Depends(get_db),
    current_user: Optional[TokenData] = Depends(get_optional_current_user)
):
    """
    Genera un itinerario básico optimizado según destino, hotel, fechas e interés.
    
    **Nuevo algoritmo híbrido con optimización de distancias:**
    - Calcula automáticamente los días desde check-in/check-out
    - Filtra tours por categoría de interés (opcional)
    - Usa scoring multinivel (rating + distancia + precio)
    - Optimiza ruta diaria con algoritmo Nearest Neighbor
    - Complejidad: O(N log N)
    
    **Campos requeridos:**
    - **destino**: Ciudad destino (ej: "Lima", "Cusco")
    - **hotel_id**: ID del hotel seleccionado
    - **fecha_checkin**: Fecha de check-in (YYYY-MM-DD)
    - **fecha_checkout**: Fecha de check-out (YYYY-MM-DD)
    
    **Campos opcionales:**
    - **interes**: Tipo de viaje (Aventura, Relajación, Cultura, Gastronomía)
    
    **Validaciones:**
    - Duración: 1-15 días
    - Hotel debe estar en el destino indicado
    - Fechas válidas (checkout > checkin)
    """
    try:
        service = ItineraryService(db)
        
        # Calcular días automáticamente
        dias = (request.fecha_checkout - request.fecha_checkin).days
        
        # Generar itinerario con nuevo algoritmo optimizado
        data = service.generar_itinerario_basico(
            destino=request.destino,
            hotel_id=request.hotel_id,
            fecha_checkin=request.fecha_checkin,
            fecha_checkout=request.fecha_checkout,
            interes=request.interes.value if request.interes else None
        )
        
        # Mensaje personalizado según autenticación
        if current_user:
            mensaje = f"Itinerario generado exitosamente para {dias} días en {request.destino}"
        else:
            mensaje = "Para guardar este itinerario y personalizarlo, regístrate gratis"
        
        return ItineraryResponse(
            success=True,
            data=data,
            mensaje=mensaje
        )
    
    except ValidationError as e:
        # Errores de validación de Pydantic
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "Debe ingresar un destino, duración e interés para generar su itinerario",
                "detalles": e.errors()
            }
        )
    
    except ValueError as e:
        # Errores de validación de negocio
        error_message = str(e)
        
        # Mensajes específicos según tipo de error
        if "no existe" in error_message.lower() or "no está" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": error_message
                }
            )
        elif "no hay actividades" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": error_message
                }
            )
        elif "coordenadas" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": "El hotel seleccionado no tiene información de ubicación. Por favor, seleccione otro hotel"
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
                "error": "El itinerario no pudo generarse. Intente nuevamente más tarde"
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
