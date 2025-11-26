from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from datetime import date
import math
from app.models.servicio import Servicio, Hotel
from app.models.tour import Tour, TourActividad
from app.models.review import Review
from app.config.settings import get_settings

settings = get_settings()


class ItineraryService:
    
    def __init__(self, db: Session):
        self.db = db
        self.horas_por_dia = settings.HORAS_DISPONIBLES_POR_DIA
    
    def _calcular_distancia_haversine(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calcula la distancia en kilómetros entre dos puntos geográficos
        usando la fórmula de Haversine.
        
        Args:
            lat1, lon1: Coordenadas del punto 1 (hotel)
            lat2, lon2: Coordenadas del punto 2 (tour)
        
        Returns:
            float: Distancia en kilómetros
        
        Complejidad: O(1)
        """
        R = 6371  # Radio de la Tierra en km
        
        # Convertir grados a radianes
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Fórmula Haversine
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distancia_km = R * c
        return round(distancia_km, 2)
    
    def _calcular_score_tour(
        self,
        tour: Dict,
        peso_rating: float = 0.5,
        peso_distancia: float = 0.3,
        peso_precio: float = 0.2
    ) -> float:
        """
        Calcula un score compuesto ponderado para un tour.
        
        Formula:
        score = (rating_norm * peso_rating + 
                 distancia_norm * peso_distancia + 
                 precio_norm * peso_precio) * 100
        
        Args:
            tour: Diccionario con datos del tour
            peso_rating: Peso para calificación (default 0.5)
            peso_distancia: Peso para distancia (default 0.3)
            peso_precio: Peso para precio (default 0.2)
        
        Returns:
            float: Score entre 0-100
        
        Complejidad: O(1)
        """
        # Normalizar rating (0-5) → (0-1)
        rating_norm = tour['promedio_estrellas'] / 5.0 if tour['promedio_estrellas'] > 0 else 0
        
        # Normalizar distancia (inverso, más cerca = mejor)
        # Asumiendo máximo 100km
        distancia_norm = max(0, 1 - (tour['distancia_km'] / 100.0))
        
        # Normalizar precio (inverso, más barato = mejor)
        # Asumiendo máximo 500 PEN
        precio_norm = max(0, 1 - (tour['precio'] / 500.0))
        
        # Score ponderado
        score = (
            rating_norm * peso_rating +
            distancia_norm * peso_distancia +
            precio_norm * peso_precio
        ) * 100
        
        # Penalización fuerte si no tiene reseñas
        if tour['promedio_estrellas'] == 0:
            score *= 0.5
        
        return round(score, 2)
    
    def _ordenar_tours_por_score(self, tours: List[Dict]) -> List[Dict]:
        """
        Ordena tours por score compuesto (mayor a menor).
        
        Complejidad: O(N log N)
        """
        # Calcular scores: O(N)
        for tour in tours:
            tour['score'] = self._calcular_score_tour(tour)
        
        # Ordenar por score: O(N log N)
        tours.sort(key=lambda x: x['score'], reverse=True)
        
        return tours
    
    def _encontrar_tour_mas_cercano(
        self,
        tours: List[Dict],
        ubicacion_actual: Tuple[float, float],
        horas_disponibles: float
    ) -> Optional[Dict]:
        """
        Encuentra el tour más cercano que cumpla restricciones de tiempo
        y tenga buen score.
        
        Algoritmo:
        1. Filtrar tours que caben en tiempo disponible
        2. Calcular score ajustado (score - penalización por distancia)
        3. Retornar tour con mejor score ajustado
        
        Complejidad: O(N) por llamada
        """
        mejor_tour = None
        mejor_score_ajustado = -999
        
        for tour in tours:
            # Verificar si cabe en el tiempo disponible
            if tour['duracion_horas'] > horas_disponibles:
                continue
            
            # Calcular distancia desde ubicación actual
            distancia = self._calcular_distancia_haversine(
                ubicacion_actual[0], ubicacion_actual[1],
                tour['ubicacion']['lat'], tour['ubicacion']['lon']
            )
            
            # Score ajustado: score base - penalización por distancia
            # Penalización: 2 puntos por cada km
            score_ajustado = tour['score'] - (distancia * 2)
            
            if score_ajustado > mejor_score_ajustado:
                mejor_tour = tour
                mejor_score_ajustado = score_ajustado
        
        return mejor_tour
    
    def _calcular_distancia_ruta(
        self,
        hotel_coords: Tuple[float, float],
        actividades: List[Dict]
    ) -> float:
        """
        Calcula la distancia total de la ruta del día.
        Incluye: hotel -> tour1 -> tour2 -> ... -> tourN -> hotel
        
        Complejidad: O(N) donde N es número de actividades
        """
        if not actividades:
            return 0.0
        
        distancia_total = 0.0
        ubicacion_actual = hotel_coords
        
        # Sumar distancias entre cada punto
        for actividad in actividades:
            ubicacion_tour = (
                actividad['ubicacion']['lat'],
                actividad['ubicacion']['lon']
            )
            distancia_total += self._calcular_distancia_haversine(
                ubicacion_actual[0], ubicacion_actual[1],
                ubicacion_tour[0], ubicacion_tour[1]
            )
            ubicacion_actual = ubicacion_tour
        
        # Sumar regreso al hotel
        distancia_total += self._calcular_distancia_haversine(
            ubicacion_actual[0], ubicacion_actual[1],
            hotel_coords[0], hotel_coords[1]
        )
        
        return round(distancia_total, 2)
    
    def _distribuir_tours_optimizado(
        self,
        tours: List[Dict],
        dias: int,
        hotel_coords: Tuple[float, float],
        fecha_checkin: date
    ) -> List[Dict]:
        """
        Distribuye tours en días usando algoritmo Nearest Neighbor.
        
        Algoritmo:
        - Para cada día, seleccionar tour más cercano al anterior
        - Minimiza distancia acumulada del itinerario
        - Considera score de calidad
        
        Complejidad: O(N * D) donde N=tours, D=días
        """
        itinerario = []
        tours_disponibles = tours.copy()
        
        for dia in range(1, dias + 1):
            horas_disponibles = self.horas_por_dia
            actividades_dia = []
            ubicacion_actual = hotel_coords  # Inicio del día en hotel
            costo_dia = Decimal('0.00')
            
            while horas_disponibles > 0 and tours_disponibles:
                # Encontrar tour más cercano que quepa en el día
                mejor_tour = self._encontrar_tour_mas_cercano(
                    tours_disponibles,
                    ubicacion_actual,
                    horas_disponibles
                )
                
                if not mejor_tour:
                    break
                
                # Agregar tour al día
                actividades_dia.append(mejor_tour)
                horas_disponibles -= mejor_tour['duracion_horas']
                costo_dia += Decimal(str(mejor_tour['precio']))
                
                # Actualizar ubicación actual
                ubicacion_actual = (
                    mejor_tour['ubicacion']['lat'],
                    mejor_tour['ubicacion']['lon']
                )
                
                # Remover de disponibles
                tours_disponibles.remove(mejor_tour)
            
            # Calcular fecha sugerida
            fecha_dia = fecha_checkin + __import__('datetime').timedelta(days=dia - 1)
            
            # Calcular distancia total del día
            distancia_total_dia = self._calcular_distancia_ruta(
                hotel_coords,
                actividades_dia
            )
            
            itinerario.append({
                "dia": dia,
                "fecha_sugerida": fecha_dia.isoformat() if actividades_dia else None,
                "actividades": actividades_dia,
                "horas_totales": self.horas_por_dia - horas_disponibles,
                "costo_total_dia": costo_dia,
                "distancia_total_dia": distancia_total_dia
            })
        
        return itinerario
    
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
    
    def _obtener_tours_con_metricas(
        self, 
        ciudad: str, 
        hotel: Hotel,
        interes: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtiene tours del destino con sus métricas calculadas.
        Ahora incluye: filtro por interés, distancia desde hotel y coordenadas reales.
        
        Complejidad: O(N) donde N es número de tours
        """
        
        # Query para obtener tours con promedio de estrellas y total de reseñas
        tours_query = self.db.query(
            Servicio.id,
            Servicio.nombre,
            Servicio.descripcion,
            Servicio.imagen_url,
            Servicio.latitud,
            Servicio.longitud,
            Tour.precio,
            Tour.categoria,
            func.coalesce(func.avg(Review.calificacion), 0).label('promedio_estrellas'),
            func.count(Review.id).label('total_resenas')
        ).join(
            Tour, Servicio.id == Tour.servicio_id
        ).outerjoin(
            Review, Servicio.id == Review.servicio_id
        ).filter(
            Servicio.tipo == 'tour',
            Servicio.activo == True,
            Servicio.ciudad == ciudad
        )
        
        # Filtrar por interés si se especifica
        if interes:
            tours_query = tours_query.filter(Tour.categoria == interes)
        
        tours_query = tours_query.group_by(
            Servicio.id,
            Servicio.nombre,
            Servicio.descripcion,
            Servicio.imagen_url,
            Servicio.latitud,
            Servicio.longitud,
            Tour.precio,
            Tour.categoria
        )
        
        tours_data = tours_query.all()
        
        # Validar coordenadas del hotel
        if not hotel.servicio.latitud or not hotel.servicio.longitud:
            raise ValueError("El hotel no tiene coordenadas geográficas configuradas")
        
        hotel_lat = float(hotel.servicio.latitud)
        hotel_lon = float(hotel.servicio.longitud)
        
        # Obtener duraciones de las actividades para cada tour
        tours_con_metricas = []
        for tour in tours_data:
            # Calcular duración total del tour sumando actividades
            duracion_total = self.db.query(
                func.coalesce(func.sum(TourActividad.duracion_min), 0)
            ).filter(
                TourActividad.servicio_id == tour.id
            ).scalar()
            
            duracion_horas = float(duracion_total) / 60.0 if duracion_total else 4.0  # Default 4 horas
            
            # Calcular distancia desde el hotel usando coordenadas reales
            if tour.latitud and tour.longitud:
                distancia_km = self._calcular_distancia_haversine(
                    hotel_lat, hotel_lon,
                    float(tour.latitud), float(tour.longitud)
                )
                tour_lat = float(tour.latitud)
                tour_lon = float(tour.longitud)
            else:
                # Penalización si no tiene coordenadas
                distancia_km = 999.99
                tour_lat = hotel_lat
                tour_lon = hotel_lon
            
            tours_con_metricas.append({
                "tour_id": tour.id,
                "nombre": tour.nombre,
                "descripcion": tour.descripcion or "",
                "categoria": tour.categoria,
                "duracion_horas": duracion_horas,
                "precio": float(tour.precio),
                "moneda": "PEN",
                "promedio_estrellas": float(tour.promedio_estrellas),
                "total_resenas": tour.total_resenas,
                "imagen_url": tour.imagen_url,
                "distancia_km": distancia_km,
                "ubicacion": {
                    "lat": tour_lat,
                    "lon": tour_lon
                }
            })
        
        return tours_con_metricas
    
    def generar_itinerario_basico(
        self,
        destino: str,
        hotel_id: int,
        fecha_checkin: date,
        fecha_checkout: date,
        interes: Optional[str] = None
    ) -> Dict:
        """
        Genera un itinerario básico optimizado usando algoritmo híbrido.
        
        Algoritmo:
        1. Validar hotel y calcular días
        2. Obtener tours con métricas (filtrado por interés si aplica)
        3. Calcular score compuesto para cada tour
        4. Distribuir tours usando Nearest Neighbor
        5. Calcular resumen
        
        Complejidad total: O(N log N) donde N = número de tours
        
        Args:
            destino: Nombre de la ciudad
            hotel_id: ID del hotel
            fecha_checkin: Fecha de inicio
            fecha_checkout: Fecha de fin
            interes: Categoría de interés (opcional)
        
        Returns:
            Dict con itinerario completo
        """
        
        # 1. Validar hotel
        hotel = self._validar_hotel(hotel_id)
        
        # 2. Validar que el hotel está en el destino correcto
        if hotel.servicio.ciudad.lower() != destino.lower():
            raise ValueError(
                f"El hotel seleccionado no está ubicado en {destino}. "
                f"El hotel está en {hotel.servicio.ciudad}"
            )
        
        # 3. Calcular días
        dias = (fecha_checkout - fecha_checkin).days
        
        # 4. Obtener tours con métricas (incluye filtro por interés)
        tours = self._obtener_tours_con_metricas(
            ciudad=hotel.servicio.ciudad,
            hotel=hotel,
            interes=interes
        )
        
        # 5. Validar que hay tours disponibles
        if not tours:
            if interes:
                raise ValueError(
                    f"No hay actividades disponibles para el tipo de interés '{interes}' en {destino}"
                )
            else:
                raise ValueError(f"No hay actividades disponibles en {destino}")
        
        # 6. FASE 1: Calcular scores y ordenar (O(N log N))
        tours_ordenados = self._ordenar_tours_por_score(tours)
        
        # 7. FASE 2: Distribuir tours optimizando ruta (O(N * D))
        hotel_coords = (
            float(hotel.servicio.latitud),
            float(hotel.servicio.longitud)
        )
        
        itinerario_dias = self._distribuir_tours_optimizado(
            tours_ordenados,
            dias,
            hotel_coords,
            fecha_checkin
        )
        
        # 8. Calcular resumen
        resumen = self._calcular_resumen_optimizado(itinerario_dias, dias)
        
        # 9. Construir respuesta
        return {
            "destino": {
                "nombre": hotel.servicio.ciudad,
                "ciudad": hotel.servicio.ciudad,
                "pais": hotel.servicio.pais
            },
            "hotel": {
                "id": hotel.servicio_id,
                "nombre": hotel.servicio.nombre,
                "direccion": hotel.direccion,
                "estrellas": hotel.estrellas
            },
            "itinerario": itinerario_dias,
            "resumen": resumen
        }
    
    def _calcular_resumen_optimizado(self, itinerario: List[Dict], dias: int) -> Dict:
        """
        Calcula el resumen del itinerario con métricas adicionales.
        
        Complejidad: O(N) donde N = total de actividades
        """
        total_tours = sum(len(dia['actividades']) for dia in itinerario)
        costo_total = sum(dia['costo_total_dia'] for dia in itinerario)
        distancia_total = sum(dia['distancia_total_dia'] for dia in itinerario)
        
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
            "promedio_valoracion": round(promedio_valoracion, 1),
            "distancia_total_km": round(distancia_total, 2)
        }
    
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
