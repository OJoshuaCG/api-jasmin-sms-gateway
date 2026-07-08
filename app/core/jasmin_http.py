import re

import httpx

from app.core import environments
from app.core.context import current_http_identifier
from app.core.logger import get_logger

logger = get_logger(__name__)

_client: httpx.AsyncClient | None = None

# Redacta el valor de cualquier `password=...` en URLs / cuerpos antes de loguear.
_PASSWORD_RE = re.compile(r"(?i)(password=)[^&\s]*")


def _redact(text: str) -> str:
    return _PASSWORD_RE.sub(r"\1***", text)


async def _log_request(request: httpx.Request) -> None:
    rid = current_http_identifier.get() or "-"
    logger.info("%s | Jasmin HTTP → %s %s", rid, request.method, _redact(str(request.url)))


async def _log_response(response: httpx.Response) -> None:
    rid = current_http_identifier.get() or "-"
    await response.aread()
    logger.info(
        "%s | Jasmin HTTP ← %s | body: %s",
        rid,
        response.status_code,
        _redact(response.text.strip()),
    )


def get_jasmin_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("JasminHttpClient not initialized")
    return _client


async def init_jasmin_http_client(host: str, port: int) -> None:
    global _client
    base_url = f"http://{host}:{port}"
    event_hooks: dict = {}
    if environments.JASMIN_LOG:
        event_hooks = {"request": [_log_request], "response": [_log_response]}
        logger.info("JASMIN_LOG activo: se trazará toda la comunicación HTTP con Jasmin")
    _client = httpx.AsyncClient(base_url=base_url, timeout=30.0, event_hooks=event_hooks)
    logger.info("Jasmin HTTP client initialized at %s", base_url)


async def close_jasmin_http_client() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None
        logger.info("Jasmin HTTP client closed")
