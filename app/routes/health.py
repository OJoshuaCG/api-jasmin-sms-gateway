from fastapi import APIRouter

from app.core.environments import APP_ENV, APP_NAME
from app.controllers.system_controller import SystemController

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    """
    Service health — no auth required.
    Returns Jasmin Telnet + HTTP API status alongside the app status.
    """
    try:
        health_data = await SystemController().health()
        return {
            "status": health_data.status,
            "service": APP_NAME,
            "environment": APP_ENV,
            "telnet": health_data.telnet.model_dump(),
            "jasmin_http": health_data.jasmin_http.model_dump(),
        }
    except Exception:
        return {
            "status": "error",
            "service": APP_NAME,
            "environment": APP_ENV,
            "telnet": {"connected": False},
            "jasmin_http": {"reachable": False},
        }
