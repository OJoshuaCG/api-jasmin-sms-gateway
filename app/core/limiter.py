from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.environments import RATE_LIMIT_DEFAULT

# Instancia compartida entre todas las versiones de la API.
# key_func=get_remote_address → el límite se aplica por IP del cliente.
# default_limits aplica globalmente a todas las rutas sin necesidad de decorador.
# Para un límite específico por ruta usa el decorador:
#   @limiter.limit("10/minute")
#   async def my_endpoint(request: Request): ...
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT_DEFAULT],
)
