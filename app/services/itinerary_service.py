from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Tuple
from decimal import Decimal
from app.models.servicio import Servicio, Hotel
from app.models.tour import Tour, TourActividad
from app.models.review import Review
from app.config.settings import get_settings

settings = get_settings()


class ItineraryService:
    
    def __init__(self, db: Session):
        self.db = db
        self.horas_por_dia = settings.HORAS_DISPONIBLES_POR_DIA
    
    def generar_itinerario(self, destination_id: int, hotel_id: int, dias: int) -> Dict:
        """Genera un itinerario completo basado en los parámetros recibidos"""
        
        # 1. Validar que el hotel existe y obtener su información
        hotel = self._validar_hotel(hotel_id)
        
        # 2. Obtener información del destino (ciudad del hotel)
        destino_info = self._obtener_destino(hotel)
        
        # 3. Obtener tours del destino con sus métricas
        # En lugar de buscar en la ciudad del hotel, buscamos en TODAS las ciudades disponibles
        # para que el itinerario incluya tours de diferentes lugares si es necesario
        tours = self._obtener_tours_con_metricas(destino_info['ciudad'])
        
        # Si no hay tours en la ciudad del hotel, buscar tours en cualquier ciudad cercana
        if not tours:
            tours = self._obtener_tours_con_metricas(None)  # Buscar en todas las ciudades
        
        if not tours:
            raise ValueError(f"No hay tours disponibles")
        
        # 4. Distribuir tours por días
        itinerario_dias = self._distribuir_tours_por_dias(tours, dias)
        
        # 5. Calcular resumen
        resumen = self._calcular_resumen(itinerario_dias, dias, tours)
        
        # 6. Construir respuesta
        return {
            "destino": destino_info,
            "hotel": {
                "id": hotel.servicio_id,
                "nombre": hotel.servicio.nombre,
                "direccion": hotel.direccion,
                "estrellas": hotel.estrellas
            },
            "itinerario": itinerario_dias,
            "resumen": resumen
        }
    
    def _validar_hotel(self, hotel_id: int) -> Hotel:
        """Valida que el hotel existe y está activo"""
        hotel = self.db.query(Hotel).join(Servicio).filter(
            Hotel.servicio_id == hotel_id,
            Servicio.tipo == 'hotel',
            Servicio.activo == True
        ).first()
        
        if not hotel:
            raise ValueError("El hotel seleccionado no existe o no está disponible")
        
        return hotel
    
    def _obtener_destino(self, hotel: Hotel) -> Dict:
        """Obtiene información del destino basado en el hotel"""
        return {
            "id": hotel.servicio_id,
            "nombre": hotel.servicio.ciudad,
            "ciudad": hotel.servicio.ciudad,
            "pais": hotel.servicio.pais
        }
    
    def _validar_destino_hotel(self, destination_id: int, hotel_id: int, ciudad: str):
        """Valida que el hotel pertenece al destino seleccionado"""
        # El destination_id debería ser un servicio de tipo hotel en la misma ciudad
        destino = self.db.query(Servicio).filter(
            Servicio.id == destination_id,
            Servicio.ciudad == ciudad,
            Servicio.activo == True
        ).first()
        
        if not destino:
            raise ValueError("El hotel seleccionado no pertenece al destino indicado")
    
    def _obtener_tours_con_metricas(self, ciudad: str = None) -> List[Dict]:
        """Obtiene tours del destino con sus métricas calculadas
        Si ciudad es None, obtiene tours de todas las ciudades"""
        
        # Query para obtener tours con promedio de estrellas y total de reseñas
        tours_query = self.db.query(
            Servicio.id,
            Servicio.nombre,
            Servicio.descripcion,
            Servicio.imagen_url,
            Tour.precio,
            func.coalesce(func.avg(Review.calificacion), 0).label('promedio_estrellas'),
            func.count(Review.id).label('total_resenas')
        ).join(
            Tour, Servicio.id == Tour.servicio_id
        ).outerjoin(
            Review, Servicio.id == Review.servicio_id
        ).filter(
            Servicio.tipo == 'tour',
            Servicio.activo == True
        )
        
        # Filtrar por ciudad solo si se especifica
        if ciudad:
            tours_query = tours_query.filter(Servicio.ciudad == ciudad)
        
        tours_query = tours_query.group_by(
            Servicio.id,
            Servicio.nombre,
            Servicio.descripcion,
            Servicio.imagen_url,
            Tour.precio
        )
        
        tours_data = tours_query.all()
        
        # Obtener duraciones de las actividades para cada tour
        tours_con_metricas = []
        for tour in tours_data:
            # Calcular duración total del tour sumando actividades
            duracion_total = self.db.query(
                func.coalesce(func.sum(TourActividad.duracion_min), 0)
            ).filter(
                TourActividad.servicio_id == tour.id
            ).scalar()
            
            duracion_horas = float(duracion_total) / 60.0 if duracion_total else 4.0  # Default 4 horas si no hay actividades
            
            tours_con_metricas.append({
                "tour_id": tour.id,
                "nombre": tour.nombre,
                "descripcion": tour.descripcion or "",
                "duracion_horas": duracion_horas,
                "precio": float(tour.precio),
                "promedio_estrellas": float(tour.promedio_estrellas),
                "total_resenas": tour.total_resenas,
                "imagen_url": tour.imagen_url,
                "ubicacion": {
                    "lat": -12.0464,  # Mock: Centro de Perú
                    "lon": -77.0428   # Mock: se puede personalizar por ciudad
                }
            })
        
        # Ordenar por promedio de estrellas (mayor a menor)
        # Tours sin reseñas (0.0) van al final
        tours_con_metricas.sort(key=lambda x: (x['promedio_estrellas'] > 0, x['promedio_estrellas']), reverse=True)
        
        return tours_con_metricas
    
    def _distribuir_tours_por_dias(self, tours: List[Dict], dias: int) -> List[Dict]:
        """Distribuye los tours en los días disponibles"""
        itinerario = []
        tour_index = 0
        
        for dia in range(1, dias + 1):
            horas_disponibles = self.horas_por_dia
            actividades_del_dia = []
            costo_dia = Decimal('0.00')
            
            # Llenar el día con tours mientras haya horas disponibles y tours
            while horas_disponibles > 0 and tour_index < len(tours):
                tour_actual = tours[tour_index]
                duracion = tour_actual['duracion_horas']
                
                # Si el tour es de día completo (8+ horas), ocupar el día completo
                if duracion >= 8:
                    if len(actividades_del_dia) == 0:  # Solo si el día está vacío
                        actividades_del_dia.append({
                            **tour_actual,
                            "moneda": "PEN"
                        })
                        costo_dia += Decimal(str(tour_actual['precio']))
                        tour_index += 1
                        horas_disponibles = 0  # Día completo ocupado
                    else:
                        break  # No cabe, pasar al siguiente día
                
                # Tour corto que cabe en el día
                elif duracion <= horas_disponibles:
                    actividades_del_dia.append({
                        **tour_actual,
                        "moneda": "PEN"
                    })
                    costo_dia += Decimal(str(tour_actual['precio']))
                    horas_disponibles -= duracion
                    tour_index += 1
                else:
                    # No cabe más en este día
                    break
            
            # Si el día tiene al menos una actividad, agregarlo
            if actividades_del_dia:
                itinerario.append({
                    "dia": dia,
                    "fecha_sugerida": None,
                    "actividades": actividades_del_dia,
                    "horas_totales": self.horas_por_dia - horas_disponibles,
                    "costo_total_dia": costo_dia
                })
            else:
                # Si no hay más tours, agregar día vacío
                itinerario.append({
                    "dia": dia,
                    "fecha_sugerida": None,
                    "actividades": [],
                    "horas_totales": 0,
                    "costo_total_dia": Decimal('0.00')
                })
        
        return itinerario
    
    def _calcular_resumen(self, itinerario: List[Dict], dias: int, tours: List[Dict]) -> Dict:
        """Calcula el resumen del itinerario"""
        total_tours = sum(len(dia['actividades']) for dia in itinerario)
        costo_total = sum(dia['costo_total_dia'] for dia in itinerario)
        
        # Calcular promedio de valoración de todos los tours incluidos
        if total_tours > 0:
            sum_valoraciones = sum(
                act['promedio_estrellas'] 
                for dia in itinerario 
                for act in dia['actividades']
                if act['promedio_estrellas'] > 0
            )
            tours_con_valoracion = sum(
                1 for dia in itinerario 
                for act in dia['actividades']
                if act['promedio_estrellas'] > 0
            )
            promedio_valoracion = sum_valoraciones / tours_con_valoracion if tours_con_valoracion > 0 else 0.0
        else:
            promedio_valoracion = 0.0
        
        return {
            "total_dias": dias,
            "total_tours": total_tours,
            "costo_total": costo_total,
            "promedio_valoracion": round(promedio_valoracion, 1)
        }
