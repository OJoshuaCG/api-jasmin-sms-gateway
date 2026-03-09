# Middlewares

Los middlewares interceptan requests y responses para agregar funcionalidad transversal. En este template cada versión de API es una sub-app independiente con su propio stack de middlewares, configurado automáticamente por `create_versioned_app()`.

## Stack Actual

El stack de middlewares se configura en `app/core/versioned_app.py`. El orden de ejecución es:

```
Request
  ↓
1. RequestSizeMiddleware   (rechaza requests muy grandes)
  ↓
2. CORSMiddleware          (valida origen, responde preflight OPTIONS)
  ↓
3. ContextMiddleware       (genera Request ID, establece ContextVars)
  ↓
4. LoggerMiddleware        (registra request/response)
  ↓
5. SlowAPIMiddleware       (aplica rate limiting)
  ↓
Router/Endpoint
```

> En Starlette, el orden de ejecución es inverso al orden de registro con `add_middleware()`. El último en registrarse es el primero en ejecutarse.

---

## 1. RequestSizeMiddleware

**Ubicación**: `app/middleware/RequestSizeMiddleware.py`

**Propósito**: Rechazar requests con body demasiado grande antes de procesarlas.

**Configuración**:

```env
REQUEST_MAX_SIZE_MB=10
```

**Funcionamiento**:
- Solo aplica a métodos con body: `POST`, `PUT`, `PATCH`
- Primero revisa el header `Content-Length` (sin leer el body)
- Si no hay `Content-Length`, lee el body completo como fallback
- Rutas excluidas configurables a nivel de código en `create_versioned_app()`

**Rutas excluidas** (ejemplo de uso):

```python
# app/core/versioned_app.py — ya configurado
v1_app = create_versioned_app(
    "v1",
    excluded_request_size_paths=["/api/v1/upload"]  # Si quisieras excluir alguna ruta
)
```

**Respuesta al superar el límite**:

```json
HTTP 413 Request Entity Too Large
{"detail": {"msg": "Request demasiado grande. Máximo: 10 MB", "type": "AppHttpException"}}
```

---

## 2. CORSMiddleware

**Ubicación**: `fastapi.middleware.cors` (nativo de Starlette)

**Propósito**: Controlar acceso desde orígenes distintos al servidor (Cross-Origin Resource Sharing).

**Configuración**:

```env
CORS_ORIGINS=http://localhost:3000,https://myapp.com
```

**Configuración actual**:

```python
CORSMiddleware(
    allow_origins=CORS_ORIGINS,   # Desde variable de entorno
    allow_credentials=True,        # Permite cookies y headers de auth
    allow_methods=["*"],           # Todos los métodos HTTP
    allow_headers=["*"],           # Todos los headers
)
```

**Advertencia `*` + `credentials=True`**: Los browsers rechazan `Access-Control-Allow-Origin: *` cuando la request incluye credenciales. Si el frontend envía cookies o `Authorization`, define orígenes específicos:

```env
# ❌ No funciona con credenciales en browser
CORS_ORIGINS=*

# ✓ Funciona con credenciales
CORS_ORIGINS=http://localhost:3000,https://myapp.com
```

Ver [CORS](cors.md) para documentación completa.

---

## 3. ContextMiddleware

**Ubicación**: `app/middleware/ContextMiddleware.py`

**Propósito**: Gestión de contexto de requests — Request ID y ContextVars.

**Funcionalidad**:
- Genera un Request ID único por request (`secrets.token_hex(8)` — 16 caracteres hex)
- Establece ContextVars con información de la request
- Inyecta header `X-Request-ID` en todas las responses
- Limpia ContextVars al finalizar (previene memory leaks)

**ContextVars disponibles** (accesibles desde cualquier parte del código):

```python
from app.core.context import (
    current_http_identifier,   # str — Request ID único
    current_request_ip,        # str — IP del cliente
    current_request_method,    # str — GET, POST, etc.
    current_request_route,     # str — /users/{user_id}
    current_user_id,           # str | None — ID del usuario autenticado
)

# Uso en cualquier endpoint o controlador
request_id = current_http_identifier.get()
client_ip = current_request_ip.get()
```

**No requiere configuración**. Siempre activo.

---

## 4. LoggerMiddleware

**Ubicación**: `app/middleware/LoggerMiddleware.py`

**Propósito**: Logging automático de requests y responses.

**Configuración**:

```env
LOGGER_MIDDLEWARE_ENABLED=True
LOGGER_MIDDLEWARE_SHOW_HEADERS=False
LOGGER_MIDDLEWARE_SHOW_QUERY_PARAMS=True
LOGGER_MIDDLEWARE_SHOW_BODY=True
LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS=True
```

| Variable | Default | Descripción |
|---|---|---|
| `LOGGER_MIDDLEWARE_ENABLED` | `True` | Activar/desactivar el middleware |
| `LOGGER_MIDDLEWARE_SHOW_HEADERS` | `False` | Incluir headers en el log |
| `LOGGER_MIDDLEWARE_SHOW_QUERY_PARAMS` | `True` | Mostrar query params (`?page=1&size=10`) |
| `LOGGER_MIDDLEWARE_SHOW_BODY` | `True` | Mostrar body del request |
| `LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS` | `True` | `False` = loggear template de ruta en vez de path real |

**Ejemplo de log generado**:

```
2026-03-08 10:30:15 [INFO] a1b2c3d4e5f6g7h8 | Host: 127.0.0.1 | Request: POST /api/v1/users | Body: {'username': 'john'} | Query: <no parameters>
2026-03-08 10:30:15 [INFO] a1b2c3d4e5f6g7h8 | Host: 127.0.0.1 | Response: POST /api/v1/users | Status: 201 | Duration: 0.156s
```

**`LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS=False`** — En vez de loggear `/api/v1/users/42`, loggea `/api/v1/users/{user_id}`. Útil para agrupar logs por ruta en herramientas de monitoreo.

**Rutas sensibles** — El body se oculta automáticamente en rutas configuradas como sensibles en el middleware (ej: `/user/login`):

```
Body: <cannot show>
```

Ver [Sistema de Logging](logging.md) para documentación completa.

---

## 5. SlowAPIMiddleware

**Ubicación**: `slowapi` (librería de terceros)

**Propósito**: Rate limiting global y por ruta.

**Configuración**:

```env
RATE_LIMIT_DEFAULT=100/minute
```

Formatos válidos: `10/second`, `100/minute`, `1000/hour`, `10000/day`

**Funciona mediante**:
- `SlowAPIMiddleware`: intercepta responses con status 429
- `app.state.limiter`: instancia compartida del `Limiter`
- `@limiter.limit()`: decorador para límites por ruta

**Por qué SlowAPI es el middleware más interno**: Se ejecuta último para que las requests rechazadas por rate limit sean completamente procesadas por ContextMiddleware y LoggerMiddleware — así tienen Request ID y se loggean con status 429.

Ver [Rate Limiting](rate-limiting.md) para documentación completa.

---

## Crear Middleware Personalizado

```python
# app/middleware/MyMiddleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Lógica pre-request
        response = await call_next(request)
        # Lógica post-response
        return response
```

**Registrar en `create_versioned_app()`**:

```python
# app/core/versioned_app.py
from app.middleware.MyMiddleware import MyMiddleware

def create_versioned_app(...):
    # ...
    versioned.add_middleware(MyMiddleware)  # Posición según necesidad
    # ...
```

### Ejemplo: Authentication Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.context import current_user_id
from app.exceptions import AppHttpException

class AuthMiddleware(BaseHTTPMiddleware):
    PROTECTED_ROUTES = ["/api/v1/profile", "/api/v1/admin"]

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in self.PROTECTED_ROUTES:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AppHttpException("No autenticado", 401)

        token = auth_header.split(" ")[1]
        user = decode_jwt_token(token)  # implementar

        if not user:
            raise AppHttpException("Token inválido", 401)

        current_user_id.set(str(user.id))
        return await call_next(request)
```

---

## Middlewares Útiles de Starlette/FastAPI

```python
# GZip — comprimir responses grandes
from fastapi.middleware.gzip import GZipMiddleware
versioned.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted Host — validar header Host
from fastapi.middleware.trustedhost import TrustedHostMiddleware
versioned.add_middleware(TrustedHostMiddleware, allowed_hosts=["myapp.com"])

# HTTPS Redirect — solo producción
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
if APP_ENV == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

---

## Mejores Prácticas

**Orden correcto** — ContextMiddleware siempre antes de LoggerMiddleware:

```python
# ✅ Correcto (registro inverso al orden de ejecución)
versioned.add_middleware(LoggerMiddleware)   # ejecuta segundo
versioned.add_middleware(ContextMiddleware)  # ejecuta primero

# ❌ Incorrecto
versioned.add_middleware(ContextMiddleware)  # ejecuta segundo — sin Request ID en logs
versioned.add_middleware(LoggerMiddleware)
```

**Operaciones ligeras** — No hacer queries a BD en middlewares, son síncronos por naturaleza y afectan todas las requests.

**No duplicar en main.py** — Los middlewares de la sub-app versionada no aplican al app principal (`main.py`). El endpoint `/health` está en el app principal y no tiene CORSMiddleware. Ver [CORS](cors.md#cors-en-health) si lo necesitas.
