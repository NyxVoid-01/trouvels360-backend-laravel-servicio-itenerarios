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

Genera un itinerario personalizado.

**Request:**
```json
{
  "destination_id": 1,
  "hotel_id": 1,
  "dias": 2
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "destino": {
      "id": 1,
      "nombre": "Lima",
      "pais": "Perú"
    },
    "hotel": {
      "id": 1,
      "nombre": "Hotel La Hacienda",
      "direccion": "...",
      "estrellas": 4
    },
    "itinerario": [
      {
        "dia": 1,
        "fecha_sugerida": null,
        "actividades": [...],
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

### Ordenamiento de Tours
- Tours ordenados por `promedio_estrellas` (calculado desde tabla `reviews`)
- Tours con promedio = 0 o sin reseñas aparecen al final

### Distribución por Días
- **Horas disponibles por día**: 8 horas (configurable)
- Tours de día completo (8+ horas) ocupan un día individual
- Tours cortos se combinan en el mismo día
- Duración calculada desde tabla `tour_actividades` (suma de `duracion_min`)

### Validaciones
- Hotel debe existir y estar activo
- Hotel debe pertenecer al destino seleccionado
- Días entre 1 y 15
- Debe haber al menos 1 tour disponible