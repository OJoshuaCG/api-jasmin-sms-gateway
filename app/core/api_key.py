import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.environments import ADMIN_API_KEY
from app.exceptions import AppHttpException

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency — validates X-API-Key header on every secured endpoint."""
    if not ADMIN_API_KEY:
        raise AppHttpException("ADMIN_API_KEY is not configured on this server", 500)
    # secrets.compare_digest prevents timing attacks that allow key enumeration
    # by ensuring comparison always takes the same time regardless of match position.
    if not api_key or not secrets.compare_digest(api_key.encode(), ADMIN_API_KEY.encode()):
        raise AppHttpException("Invalid or missing API key", 401)
