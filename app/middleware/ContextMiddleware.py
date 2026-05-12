import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import (
    current_http_identifier,
    current_request_client_host,
    current_request_host,
    current_request_ip,
    current_request_method,
    current_request_route,
    current_request_user_agent,
)


class ContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Generar un ID único para la solicitud (Correlation ID)
        request_id = secrets.token_hex(8)

        # 2. Establecer variables de contexto.
        # No usamos tokens ni reset() en finally: el reset ocurría en el task padre
        # antes de que la excepción llegara a ServerErrorMiddleware, dejando el
        # ContextVar en None para los exception handlers. Cada nueva request
        # sobrescribe el valor con set(), por lo que no hay fuga de estado entre requests.
        current_http_identifier.set(request_id)
        current_request_ip.set(request.client.host if request.client else "unknown")
        current_request_method.set(request.method)
        current_request_route.set(request.url.path)
        current_request_client_host.set(request.client.host if request.client else None)
        current_request_host.set(request.url.hostname)
        current_request_user_agent.set(request.headers.get("user-agent"))

        # Inyectar el ID en el request state para acceso fácil si es necesario
        request.state.request_id = request_id

        response = await call_next(request)

        # 3. Inyectar el header X-Request-ID en la respuesta para trazabilidad
        response.headers["X-Request-ID"] = request_id

        return response
