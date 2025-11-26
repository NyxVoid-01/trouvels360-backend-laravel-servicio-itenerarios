# Servicio de Itinerarios - Trouvels360

Servicio FastAPI para generación automática de itinerarios turísticos basados en valoraciones de usuarios.

## Requisitos

- Docker y Docker Compose
- (Opcional) Python 3.11 si quieres ejecutar sin Docker

## 🐳 Ejecución con Docker (Recomendado)

Debes tener corriendo backend de Laravel:

```bash
# El servicio se conectará a mysql:3306 (nombre del contenedor de Docker)
docker-compose up -d --build
```

### Verificar que está corriendo

```bash
docker ps
```

Deberías ver el contenedor `trouvels360-itinerarios` corriendo.

### Ver logs en tiempo real

```bash
docker-compose logs -f itinerarios-api
```

### Detener los servicios

```bash
docker-compose down
```

### Reconstruir después de cambios en el código

```bash
docker-compose up -d --build
```

**El servicio estará disponible en**: `http://localhost:8001`

---

## 📚 Documentación API

Una vez iniciado el servidor, accede a:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Endpoints

### POST `/api/itinerary`

Genera un itinerario personalizado con optimización de rutas por distancia y scoring.

**Request:**
```json
{
  "destino": "Lima",
  "hotel_id": 1,
  "fecha_checkin": "2025-12-01",
  "fecha_checkout": "2025-12-04",
  "interes": "Cultura"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "destino": {
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
        "fecha": "2025-12-01",
        "actividades": [
          {
            "tour_id": 310,
            "nombre": "Tour Centro Histórico de Lima",
            "descripcion": "Recorrido guiado...",
            "duracion_horas": 4,
            "precio": 80.00,
            "promedio_valoracion": 4.5,
            "distancia_km": 0.0,
            "score": 93.47
          }
        ],
        "horas_totales": 4.0,
        "costo_total_dia": 80.00,
        "distancia_total_dia": 0.0
      }
    ],
    "resumen": {
      "total_dias": 3,
      "total_tours": 4,
      "costo_total": 320.00,
      "promedio_valoracion": 4.5
    }
  },
  "mensaje": "Itinerario generado exitosamente"
}
```

### GET `/api/health`

Verifica el estado del servicio.

**Response:**
```json
{
  "status": "healthy",
  "service": "Itinerarios Service",
  "version": "1.0.0"
}
```

## Lógica de Negocio

### Sistema de Optimización Híbrido

El sistema utiliza un algoritmo híbrido de dos fases para generar itinerarios optimizados:

#### Fase 1: Scoring Multi-Criterio O(N log N)
Cada tour recibe un **score** calculado con:
- **50%** Valoración (promedio de reviews)
- **30%** Distancia desde el hotel (menor distancia = mayor score)
- **20%** Precio (menor precio = mayor score)

**Fórmula**: `score = (rating_score × 0.5 + distance_score × 0.3 + price_score × 0.2) × 100`

#### Fase 2: Nearest Neighbor O(N × D)
- Selecciona el tour con mayor score para el primer día
- Para días siguientes, elige el tour más cercano al último tour visitado
- Minimiza distancias entre tours consecutivos
- Optimiza el recorrido geográfico del itinerario

### Cálculo de Distancias
- **Fórmula de Haversine**: Calcula distancia en km entre coordenadas GPS
- Radio de la Tierra: 6371 km
- Campos utilizados: `latitud`, `longitud` (DECIMAL 10,6)

### Filtrado por Interés
Tours filtrados por categoría:
- **Aventura**: Tours de actividades extremas y deportes
- **Relajación**: Spas, playas, retiros
- **Cultura**: Museos, sitios históricos, tours patrimoniales
- **Gastronomía**: Tours culinarios, mercados, clases de cocina

### Distribución por Días
- **Horas disponibles por día**: 8 horas (configurable)
- Tours de día completo (8+ horas) ocupan un día individual
- Tours cortos se combinan en el mismo día
- Duración calculada desde campo `duracion` (minutos)

### Validaciones
- Hotel debe existir y estar activo
- Hotel debe pertenecer al destino seleccionado
- Fecha checkout debe ser posterior a checkin
- Estadía entre 1 y 15 días
- Debe haber al menos 1 tour disponible con el interés seleccionado

### Complejidad Algorítmica
- **Ordenamiento inicial**: O(N log N) - donde N = tours disponibles
- **Distribución por días**: O(N × D) - donde D = días del itinerario
- **Complejidad total**: O(N log N + N × D)
- **Caso típico**: N=20 tours, D=3 días → ~100 operaciones