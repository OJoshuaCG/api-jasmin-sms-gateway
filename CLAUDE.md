# Jasmin SMS Gateway Admin API — Guía para Agentes de IA

Este documento proporciona contexto y guías para agentes de IA que trabajen en este proyecto.

## Descripción del Proyecto

**API REST sidecar para administración y envío de SMS a través de Jasmin SMS Gateway.** Encapsula `jcli` (Telnet CLI de Jasmin) y la HTTP API de Jasmin detrás de una interfaz REST autenticada con API Key.

El sidecar vive en el mismo servidor o pod que Jasmin. Jasmin **nunca** expone sus puertos directamente al exterior.

```
Sistema externo (orchestrator, admin panel)
        │  HTTP + X-API-Key
        ▼
  jasmin-admin-api  :8080
        │
        ├── Telnet localhost:8990 ──► jcli (administración)
        └── HTTP   localhost:1401 ──► /send, /rate, /balance (envío)
                        │
                  Jasmin SMS Gateway
```

## Arquitectura

**Routes → Controllers → Jasmin** (sin base de datos propia)

- **Routes** (`app/routes/v1/`): Definen endpoints, validan entrada con Pydantic schemas
- **Controllers** (`app/controllers/`): Lógica de negocio, traduce REST ↔ jcli/HTTP
- **`jasmin_telnet.py`**: Sesión Telnet persistente con jcli (singleton)
- **`jasmin_parsers.py`**: Parsers de texto jcli → dict Python
- **`jasmin_http.py`**: Cliente HTTP async hacia `/send`, `/rate`, `/balance` de Jasmin

Cada versión de API es una **sub-app FastAPI independiente** montada en `main.py`:

```
main.py
  ├── GET /health          ← sin auth, sin middlewares de versión
  └── /api/v1 → v1_app    ← sub-app con middlewares, auth, rate limiting
```

## Estructura de Carpetas

```
app/
├── core/
│   ├── environments.py       # Todas las variables de entorno
│   ├── jasmin_telnet.py      # Sesión Telnet persistente con jcli
│   ├── jasmin_http.py        # Cliente HTTP hacia Jasmin (envío)
│   ├── jasmin_parsers.py     # Parsers de texto jcli → dict Python
│   ├── logger.py             # Logger centralizado
│   ├── context.py            # ContextVars de request (Request ID, IP)
│   └── versioned_app.py      # Factory create_versioned_app()
├── controllers/
│   ├── groups_controller.py
│   ├── users_controller.py
│   ├── smpp_connectors_controller.py
│   ├── http_connectors_controller.py
│   ├── filters_controller.py
│   ├── mt_routes_controller.py
│   ├── mo_routes_controller.py
│   ├── mt_interceptors_controller.py
│   ├── mo_interceptors_controller.py
│   ├── smpp_server_controller.py   # Lee /etc/jasmin/jasmin.cfg (no jcli)
│   ├── stats_controller.py
│   ├── sms_controller.py
│   └── system_controller.py
├── routes/v1/                # Un archivo por módulo
├── schemas/                  # Schemas Pydantic
├── exceptions/
│   ├── AppHttpException.py
│   └── HandlerExceptions.py
├── middleware/
└── utils/
    └── response.py           # ApiResponse[T], success(), empty()
```

## Comunicación con Jasmin

### jcli vía Telnet (`jasmin_telnet.py`)

La sesión Telnet es un **singleton global** con reconexión automática. Todos los controladores de administración la usan:

```python
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError

telnet = JasminTelnetSession.get_instance()
output = await telnet.execute("user --list")
await telnet.persist()  # guarda config en disco
```

Si la sesión está caída, `execute()` lanza `TelnetNotConnectedError` → el controlador debe capturarla y relanzar como `AppHttpException(..., 503)`.

**Comandos jcli disponibles** (solo estos existen):

| Comando | Descripción |
|---------|-------------|
| `user` | Gestión de usuarios |
| `group` | Gestión de grupos |
| `filter` | Gestión de filtros |
| `smppccm` | Conectores SMPP salientes |
| `httpccm` | Conectores HTTP |
| `mtrouter` | Rutas de mensajes salientes (MT) |
| `morouter` | Rutas de mensajes entrantes (MO) |
| `mtinterceptor` | Interceptores MT |
| `mointerceptor` | Interceptores MO |
| `stats` | Estadísticas en tiempo real |
| `persist` | Guardar configuración en disco |
| `load` | Recargar configuración desde disco |

**`smppserver` NO existe en jcli.** La config del servidor SMPP inbound vive en `/etc/jasmin/jasmin.cfg` y solo se puede leer (no modificar vía API).

### Comandos `stats` de jcli

```bash
stats --smppcs           # resumen de todos los conectores SMPP (tabular)
stats --smppc=<CID>      # detalle de un conector SMPP específico (KV)
stats --users            # resumen de todos los usuarios (tabular)
stats --user=<UID>       # detalle de un usuario específico (3 columnas)
stats --httpapi          # estadísticas de la HTTP API (KV)
stats --smppsapi         # estadísticas del servidor SMPP inbound (KV)
```

`stats --list` **no existe**. Para el endpoint `GET /stats/` se hacen 4 llamadas en paralelo y se agrega el resultado en `GlobalStatsOut`.

El output de `stats --user=<UID>` es especial: 3 columnas `#Item  Type  Value` donde `Type` es `"SMPP Server"` o `"HTTP Api"`. El campo `bound_connections_count` contiene un JSON dict como valor.

### HTTP API de Jasmin (`jasmin_http.py`)

Solo para envío de SMS. Jasmin ≥0.10 cambió a JSON en `/balance` y `/rate`:

- `GET /balance` → JSON `{"balance": float, "sms_count": "ND"|int}`
- `GET /rate` → JSON `{"unit_rate": float, "submit_sm_count": int}` en 200; texto en 412
- `GET /send` → texto `Success "msgid"` o `Error "reason"` (sin cambio)

Los controladores implementan parsing dual: JSON primero, fallback a texto legacy.

## Patrones de Controladores

### Controlador típico (jcli)

```python
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.jasmin_parsers import extract_error_message, is_success
from app.exceptions import AppHttpException

def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()

class GroupsController:

    async def list(self) -> list[GroupOut]:
        try:
            output = await _telnet().execute("group --list")
        except TelnetNotConnectedError as exc:
            raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})
        return parse_groups(output)

    async def create(self, data: GroupCreate) -> GroupOut:
        try:
            output = await _telnet().execute(f"group --add -g {data.gid}")
            if not is_success(output):
                raise AppHttpException(extract_error_message(output), 400)
            await _telnet().persist()
        except TelnetNotConnectedError as exc:
            raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})
        return GroupOut(gid=data.gid)
```

### Auto-persist

Cada operación de escritura exitosa llama a `await _telnet().persist()` automáticamente. Si `persist` falla, la operación completa falla. Esto garantiza que la config sobrevive reinicios.

### Parsers (`jasmin_parsers.py`)

Los parsers convierten texto jcli a dicts Python. Funciones clave:

- `is_success(output)` — True si el output contiene indicador de éxito
- `extract_error_message(output)` — extrae el mensaje de error del output
- `parse_groups(output)` / `parse_users(output)` / etc. — parsers por módulo
- `parse_stats_smppc(output, cid)` — KV format `#Key Value`
- `parse_stats_user(output, uid)` — 3-column format, maneja JSON dict en Value
- `parse_stats_smppcs(output)` / `parse_stats_users(output)` — tabular summary

## Convenciones del Proyecto

### Formato de Respuestas

**SIEMPRE** usar `ApiResponse[T]` y los helpers `success()`, `empty()`:

```python
from app.utils.response import ApiResponse, success, empty

# Datos
return success(data=obj)
return success(data=obj, message="Creado exitosamente")

# Sin datos (DELETE, acciones)
return empty("Eliminado exitosamente")
```

Los campos `None` se excluyen automáticamente del JSON. No usar `response_model_exclude_none=True`.

### Errores

**SIEMPRE** usar `AppHttpException`:

```python
from app.exceptions import AppHttpException

raise AppHttpException("Recurso no encontrado", 404, {"id": resource_id})
raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})
```

Nunca usar `HTTPException` de FastAPI directamente.

### Logging

```python
from app.core.logger import get_logger
from app.core.context import current_http_identifier

logger = get_logger(__name__)
request_id = current_http_identifier.get()
logger.info(f"{request_id} | Operación completada")
```

## Variables de Entorno (`app/core/environments.py`)

```python
# App
APP_ENV        # development | production
APP_NAME
SECRET_KEY
DOCS_ENABLED   # True/False

# Autenticación
API_KEY        # Header X-API-Key requerido en todos los endpoints excepto /health

# Jasmin Telnet (jcli)
JASMIN_TELNET_HOST    # default: 127.0.0.1
JASMIN_TELNET_PORT    # default: 8990
JASMIN_TELNET_USER    # default: jcliadmin
JASMIN_TELNET_PASSWORD
JASMIN_TELNET_TIMEOUT # segundos por comando, default: 10

# Jasmin HTTP API (envío)
JASMIN_HTTP_HOST      # default: localhost
JASMIN_HTTP_PORT      # default: 1401

# DLR centralizado
DLR_ENABLED           # default: False. Si True, la URL del DLR la fija el gateway (no el cliente)
DLR_URL               # URL base del webhook que recibe los delivery receipts
DLR_METHOD            # GET | POST (dlr-method hacia Jasmin), default: POST
DLR_LEVEL             # 1 | 2 | 3, default: 3
DLR_DEFAULT_PARAMS    # JSON dict de params fijos concatenados siempre a DLR_URL (opcional)

# Interceptores
JASMIN_SCRIPTS_DIR    # default: /etc/jasmin/scripts

# Logger
LOGGER_LEVEL
LOGGER_MIDDLEWARE_ENABLED
LOGGER_MIDDLEWARE_SHOW_HEADERS
LOGGER_MIDDLEWARE_SHOW_BODY
LOGGER_MIDDLEWARE_ERRORS_ONLY

# CORS
CORS_ORIGINS   # separados por coma, "*" para todos

# Rate Limiting
RATE_LIMIT_DEFAULT  # "200/minute"

# Request Size
REQUEST_MAX_SIZE_MB  # default: 10
```

## Limitaciones Conocidas de Jasmin

- **jcli es single-threaded**: los comandos se serializan con un lock. Operaciones simultáneas se encolan.
- **`smppserver` no existe en jcli**: `SmppServerController` lee `/etc/jasmin/jasmin.cfg` con `configparser`. `PATCH /smpp-server/` retorna 501.
- **`filter --update` no existe**: `PATCH /filters/{fid}` hace delete interno + recrear.
- **`mtrouter --update` no existe**: `PATCH /mt-routes/{order}` hace flush + recrear.
- **FIDs de filtros no recuperables**: Jasmin no expone FIDs en `route -s`. Las respuestas de GET de rutas siempre muestran `filters: []`.
- **DefaultRoute siempre order 0**: Jasmin ignora el order enviado para DefaultRoute.
- **Stats se resetean al reiniciar Jasmin**: no persisten entre reinicios.
- **Scripts de interceptores persisten en disco**: al eliminar un interceptor, el `.py` no se elimina.
- **`return` a nivel de módulo es inválido** en scripts de interceptores (Python lo rechaza en compilación).

## Agregar un Nuevo Módulo Jasmin

1. **Schema** (`app/schemas/<modulo>.py`) — `<Modulo>Create`, `<Modulo>Update`, `<Modulo>Out`
2. **Controller** (`app/controllers/<modulo>_controller.py`) — usa `_telnet().execute()`, captura `TelnetNotConnectedError`
3. **Parser** en `app/core/jasmin_parsers.py` — convierte output de jcli a dict
4. **Routes** (`app/routes/v1/<modulo>.py`) — usa `ApiResponse[T]`, `success()`, `empty()`
5. **Registrar** en `app/routes/v1/__init__.py`

## Flujos de Mensajes

### Saliente (MT)

```
POST /sms/send
    → Proxy a Jasmin HTTP localhost:1401/send
    → Jasmin autentica usuario (username/password)
    → Jasmin ejecuta MT Interceptors
    → Jasmin evalúa MT Routes → selecciona SMPP Connector
    → Carrier recibe el SMS
    → (async) DLR callback al dlr_url del cliente
```

### Entrante (MO)

```
Usuario final envía SMS al carrier
    → Carrier → SMPP bind de Jasmin
    → Jasmin ejecuta MO Interceptors
    → Jasmin evalúa MO Routes → selecciona HTTP Connector
    → POST/GET al webhook configurado en el HTTP Connector
```

## Tecnologías

- **Python 3.13+**
- **FastAPI** con sub-app mounting para API versioning
- **Pydantic v2** — validación y schemas
- **httpx** — cliente HTTP async para proxy a Jasmin HTTP
- **slowapi** — rate limiting
- **uv** — gestor de paquetes

## Comandos Útiles

```bash
# Desarrollo
uv run uvicorn main:app --reload --port 8080

# Producción
uv run uvicorn main:app --host 0.0.0.0 --port 8080

# Dependencias
uv add <paquete>
uv sync
```

## Documentación

- `readme.md` — instalación, quick start, referencia de endpoints
- `docs/jasmin/` — documentación detallada por módulo (grupos, usuarios, conectores, etc.)
- Swagger en `/api/v1/docs` | ReDoc en `/api/v1/redoc` (si `DOCS_ENABLED=True`)

---

**Nota para Agentes**: Todo endpoint usa `ApiResponse[T]`. Todo error usa `AppHttpException`. La comunicación con Jasmin es exclusivamente vía `jasmin_telnet.py` (admin) o `jasmin_http.py` (envío). No hay base de datos propia. Consulta `docs/jasmin/` para semántica de cada módulo.
