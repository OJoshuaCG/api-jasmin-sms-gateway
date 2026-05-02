from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.environments import ADMIN_API_KEY
from app.exceptions import AppHttpException

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency — validates X-API-Key header on every secured endpoint."""
    if not ADMIN_API_KEY:
        raise AppHttpException("ADMIN_API_KEY is not configured on this server", 500)
    if not api_key or api_key != ADMIN_API_KEY:
        raise AppHttpException("Invalid or missing API key", 401)
