import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)

_client: httpx.AsyncClient | None = None


def get_jasmin_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("JasminHttpClient not initialized")
    return _client


async def init_jasmin_http_client(host: str, port: int) -> None:
    global _client
    base_url = f"http://{host}:{port}"
    _client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    logger.info("Jasmin HTTP client initialized at %s", base_url)


async def close_jasmin_http_client() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None
        logger.info("Jasmin HTTP client closed")
