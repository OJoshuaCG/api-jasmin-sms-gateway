# Rate Limiting

## Configuración Global

El rate limiting se aplica automáticamente a todas las rutas de cada versión vía `SlowAPIMiddleware`. No requiere cambios en los endpoints.

```env
RATE_LIMIT_DEFAULT=100/minute
```

Formatos válidos: `10/second`, `100/minute`, `1000/hour`, `10000/day`

## Límite por Ruta Específica

Para sobrescribir el límite global en un endpoint concreto, usar el decorador `@limiter.limit()`. **Requiere `request: Request` como parámetro.**

```python
from fastapi import Request
from app.core.limiter import limiter

@router.post("/login")
@limiter.limit("5/minute")           # Límite más estricto para login
async def login(request: Request, credentials: LoginSchema):
    ...

@router.get("/public-data")
@limiter.limit("500/minute")         # Límite más permisivo para datos públicos
async def get_public_data(request: Request):
    ...
```

## Respuesta al Exceder el Límite

```json
HTTP 429 Too Many Requests
{
  "detail": {
    "msg": "Demasiadas solicitudes. Límite: 100 per 1 minute",
    "type": "RateLimitExceeded"
  }
}
```

## Identificación por IP

El límite se aplica por IP del cliente (`get_remote_address` de slowapi). Si tu app está detrás de un proxy/load balancer, asegúrate de que el header `X-Forwarded-For` esté configurado correctamente para obtener la IP real del cliente.

## Logging de Rate Limit

Si `LOGGER_EXCEPTIONS_ENABLED=True`, cada request rechazado por rate limit genera un log:

```
[WARNING] abc123 | Exception: RateLimitExceeded | Limit: 100 per 1 minute | IP: 1.2.3.4
```

## Instancia Compartida

El `Limiter` es un singleton en `app/core/limiter.py` compartido entre todas las versiones. Los contadores se mantienen en memoria por proceso — para múltiples workers (producción), considera configurar un backend Redis:

```python
# app/core/limiter.py — configuración con Redis (opcional)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri="redis://localhost:6379",  # Para múltiples workers
)
```
