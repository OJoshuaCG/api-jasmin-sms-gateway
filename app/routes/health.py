from fastapi import APIRouter

from app.core.environments import APP_ENV, APP_NAME

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """
    Endpoint de salud de la aplicación.
    No está versionado ni tiene rate limiting.
    Útil para health checks de Docker, Kubernetes, load balancers, etc.
    """
    return {
        "status": "ok",
        "service": APP_NAME,
        "environment": APP_ENV,
    }
