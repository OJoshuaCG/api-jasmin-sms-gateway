import time
from urllib.parse import parse_qsl, urlencode

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import current_http_identifier
from app.core.environments import (
    LOGGER_MIDDLEWARE_ERRORS_ONLY,
    LOGGER_MIDDLEWARE_SHOW_BODY,
    LOGGER_MIDDLEWARE_SHOW_HEADERS,
    LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS,
    LOGGER_MIDDLEWARE_SHOW_QUERY_PARAMS,
)
from app.core.logger import get_logger

logger = get_logger()

_SENSITIVE_PATHS = {"/user/login"}
_REDACTED_HEADERS = {"x-api-key", "authorization", "cookie", "set-cookie"}
# Query params that must never appear in logs (e.g. Jasmin user passwords on SMS endpoints)
_REDACTED_QUERY_PARAMS = {"password"}


def _redact_query_params(query_string: str) -> str:
    """Replace sensitive query param values with *** before logging."""
    parts = parse_qsl(query_string, keep_blank_values=True)
    redacted = [
        (k, "***" if k.lower() in _REDACTED_QUERY_PARAMS else v)
        for k, v in parts
    ]
    return urlencode(redacted)


class LoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        unique_id = current_http_identifier.get()
        start_time = time.time()

        method = request.method
        path = request.url.path
        raw_query = request.url.query or None
        query_string = _redact_query_params(raw_query) if raw_query else None
        headers = {
            k: ("***" if k.lower() in _REDACTED_HEADERS else v)
            for k, v in request.headers.items()
        }
        client_ip = request.client.host if request.client else "unknown"

        try:
            body = await request.json()
        except Exception:
            body = "<no body>"

        response = await call_next(request)
        process_time = round(time.time() - start_time, 3)

        if LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS:
            display_path = path
        else:
            route = request.scope.get("route")
            display_path = route.path if route else path

        is_error = response.status_code >= 400

        if LOGGER_MIDDLEWARE_ERRORS_ONLY and not is_error:
            return response

        # REQUEST
        request_parts = [
            str(unique_id),
            f"Host: {client_ip}",
            f"Request: {method} {display_path}",
        ]
        if LOGGER_MIDDLEWARE_SHOW_BODY:
            request_parts.append(
                f"Body: {'<cannot show>' if path in _SENSITIVE_PATHS else body}"
            )
        if LOGGER_MIDDLEWARE_SHOW_QUERY_PARAMS:
            request_parts.append(
                f"Query: {query_string if query_string else '<no parameters>'}"
            )
        if LOGGER_MIDDLEWARE_SHOW_HEADERS:
            request_parts.append(f"Headers: {headers}")

        logger.info(" | ".join(request_parts))

        # ERROR (solo cuando hay error)
        if is_error:
            error_parts = [
                str(unique_id),
                f"Host: {client_ip}",
                f"Error: {method} {display_path}",
                f"Status: {response.status_code}",
            ]
            if response.status_code >= 500:
                logger.error(" | ".join(error_parts))
            else:
                logger.warning(" | ".join(error_parts))

        # RESPONSE
        response_parts = [
            str(unique_id),
            f"Host: {client_ip}",
            f"Response: {method} {display_path}",
            f"Status: {response.status_code}",
            f"Duration: {process_time}s",
        ]
        logger.info(" | ".join(response_parts))

        return response
