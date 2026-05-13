# Jasmin SMS Gateway — Admin API

> **API REST sidecar para administración y envío de SMS a través de Jasmin SMS Gateway. Encapsula jcli (Telnet) y la HTTP API de Jasmin detrás de una interfaz REST autenticada con API Key.**

---

## Qué es

`jasmin-admin-api` vive en el mismo servidor o pod que Jasmin y actúa como su **único punto de acceso externo**. Jasmin nunca expone sus puertos directamente al exterior.

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

---

## Módulos implementados

| Módulo | Endpoints base | Descripción |
|--------|---------------|-------------|
| Grupos | `/groups` | Grupos de usuarios Jasmin |
| Usuarios | `/users` | Credenciales, balance y límites por usuario |
| Conectores SMPP | `/smpp-connectors` | Conexiones salientes al carrier/SMSC |
| Conectores HTTP | `/http-connectors` | Destinos de entrega de mensajes MO |
| Filtros | `/filters` | Condiciones de selección de mensajes |
| Rutas MT | `/mt-routes` | Routing de mensajes salientes |
| Rutas MO | `/mo-routes` | Routing de mensajes entrantes |
| Interceptores MT | `/mt-interceptors` | Scripts Python sobre mensajes salientes |
| Interceptores MO | `/mo-interceptors` | Scripts Python sobre mensajes entrantes |
| SMPP Server | `/smpp-server` | Config del servidor SMPP inbound (solo lectura) |
| Estadísticas | `/stats` | Métricas en tiempo real (solo lectura) |
| Sistema | `/system` | Persist, reload, reconexión Telnet |
| SMS | `/sms` | Envío, balance y tarifa (proxy a Jasmin HTTP) |
| Salud | `/health` | Estado del servicio (sin auth) |

---

## Inicio Rápido

### 1. Instalar dependencias

```bash
# Requiere uv — https://docs.astral.sh/uv/
uv sync
```

### 2. Configurar entorno

```bash
cp .env.example .env
# Editar .env con los valores de tu instancia Jasmin
```

### 3. Ejecutar

```bash
# Desarrollo con hot-reload
uv run uvicorn main:app --reload --port 8080

# Producción
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

### 4. Verificar

```bash
curl http://localhost:8080/health
# {"status":"ok","telnet":{"connected":true,...},"jasmin_http":{"reachable":true}}
```

---

## Variables de Entorno

Documentadas en `.env.example`. Resumen completo:

```env
# ======= App =======
APP_ENV=production             # development | production
APP_NAME="Jasmin Admin API"
SECRET_KEY=                    # python -c "import secrets; print(secrets.token_hex(32))"
DOCS_ENABLED=True              # False deshabilita /docs y /redoc

# ======= API Key (autenticación) =======
API_KEY=                       # Header X-API-Key requerido en todos los endpoints excepto /health

# ======= Jasmin Telnet (jcli) =======
JASMIN_TELNET_HOST=127.0.0.1
JASMIN_TELNET_PORT=8990
JASMIN_TELNET_USER=jcliadmin
JASMIN_TELNET_PASSWORD=jclipwd
JASMIN_TELNET_TIMEOUT=10       # Segundos por comando

# ======= Jasmin HTTP API (envío) =======
JASMIN_HTTP_HOST=localhost
JASMIN_HTTP_PORT=1401

# ======= Scripts de interceptores =======
JASMIN_SCRIPTS_DIR=/etc/jasmin/scripts  # Directorio donde se guardan los scripts Python

# ======= Logger =======
LOGGER_LEVEL=INFO
LOGGER_MIDDLEWARE_ENABLED=True
LOGGER_MIDDLEWARE_SHOW_HEADERS=False
LOGGER_MIDDLEWARE_SHOW_BODY=False
LOGGER_MIDDLEWARE_ERRORS_ONLY=False     # True = solo loggea errores 4xx/5xx

# ======= CORS =======
CORS_ORIGINS=*                 # Separados por coma

# ======= Rate Limiting =======
RATE_LIMIT_DEFAULT=200/minute

# ======= Request Size =======
REQUEST_MAX_SIZE_MB=10
```

---

## Autenticación

Todos los endpoints excepto `GET /health` requieren el header:

```
X-API-Key: <tu-api-key>
```

Sin este header o con valor incorrecto, la API retorna `401`.

---

## Formato de Respuesta

**Éxito:**
```json
{"data": {...}}
{"data": [...]}
{"message": "Operación completada"}
{"data": {...}, "message": "Creado exitosamente"}
```

**Error:**
```json
{"detail": {"msg": "Descripción del error", "type": "AppHttpException"}}
{"detail": {"msg": "Error de validación en: campo", "type": "RequestValidationError"}}
```

**Códigos HTTP:**

| Código | Significado |
|--------|-------------|
| 200 | OK |
| 201 | Creado |
| 400 | Error de Jasmin o parámetros inválidos |
| 401 | API Key ausente o inválida |
| 404 | Recurso no encontrado |
| 409 | Conflicto (ya existe) |
| 422 | Error de validación Pydantic |
| 501 | No implementado (ej: PATCH /smpp-server) |
| 503 | Jasmin no disponible (Telnet desconectado) |

---

## Estructura del Proyecto

```
app/
├── core/
│   ├── environments.py       # Todas las variables de entorno
│   ├── jasmin_telnet.py      # Sesión Telnet persistente con Jasmin (jcli)
│   ├── jasmin_http.py        # Cliente HTTP hacia la API de Jasmin (envío)
│   ├── jasmin_parsers.py     # Parsers de texto jcli → dict Python
│   ├── logger.py             # Logger centralizado
│   ├── context.py            # ContextVars de request (Request ID, IP)
│   └── versioned_app.py      # Factory de sub-apps versionadas
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
│   ├── smpp_server_controller.py   # Lee desde /etc/jasmin/jasmin.cfg
│   ├── stats_controller.py
│   ├── sms_controller.py
│   └── system_controller.py
├── routes/v1/                # Un archivo de rutas por módulo
├── schemas/                  # Schemas Pydantic con descripciones de campos
├── exceptions/
│   ├── AppHttpException.py   # Excepción personalizada con tracking
│   └── HandlerExceptions.py  # Handlers globales
├── middleware/               # Context, Logger, RequestSize
└── utils/
    └── response.py           # ApiResponse[T], success(), empty()
```

---

## Flujo de un Mensaje Saliente (MT)

```
POST /sms/send
    → Proxy a Jasmin HTTP localhost:1401/send
    → Jasmin autentica usuario (username/password)
    → Jasmin ejecuta MT Interceptors
    → Jasmin evalúa MT Routes → selecciona SMPP Connector
    → Carrier recibe el SMS
    → (async) DLR callback al dlr_url del cliente
```

## Flujo de un Mensaje Entrante (MO)

```
Usuario final envía SMS al carrier
    → Carrier → SMPP bind de Jasmin
    → Jasmin ejecuta MO Interceptors
    → Jasmin evalúa MO Routes → selecciona HTTP Connector
    → POST/GET al webhook configurado en el HTTP Connector
```

---

## Orden de Configuración

Para que el gateway funcione, crear los recursos en este orden:

```
1. Grupos                → POST /groups/
2. Usuarios              → POST /users/
3. Filtros               → POST /filters/           (si se usan rutas/interceptores con filtros)
4. Conectores SMPP       → POST /smpp-connectors/   (para MT)
5. Conectores HTTP       → POST /http-connectors/   (para MO)
6. Rutas MT              → POST /mt-routes/
7. Rutas MO              → POST /mo-routes/
8. Interceptores         → POST /mt-interceptors/ / /mo-interceptors/  (opcional)
```

Después de cualquier cambio, Jasmin persiste automáticamente la configuración en disco.

---

## Referencia rápida de endpoints

### Grupos
```
GET    /api/v1/groups/
GET    /api/v1/groups/{gid}
POST   /api/v1/groups/
PATCH  /api/v1/groups/{gid}          {"enabled": bool}
DELETE /api/v1/groups/{gid}
```

### Usuarios
```
GET    /api/v1/users/
GET    /api/v1/users/{uid}
POST   /api/v1/users/
PATCH  /api/v1/users/{uid}
PATCH  /api/v1/users/{uid}/status    {"enabled": bool}
DELETE /api/v1/users/{uid}
```

### Conectores SMPP
```
GET    /api/v1/smpp-connectors/
GET    /api/v1/smpp-connectors/{cid}
POST   /api/v1/smpp-connectors/
PATCH  /api/v1/smpp-connectors/{cid}
DELETE /api/v1/smpp-connectors/{cid}
GET    /api/v1/smpp-connectors/{cid}/status
POST   /api/v1/smpp-connectors/{cid}/start
POST   /api/v1/smpp-connectors/{cid}/stop
```

### Conectores HTTP
```
GET    /api/v1/http-connectors/
GET    /api/v1/http-connectors/{cid}
POST   /api/v1/http-connectors/
PATCH  /api/v1/http-connectors/{cid}
DELETE /api/v1/http-connectors/{cid}
```

### Filtros
```
GET    /api/v1/filters/
GET    /api/v1/filters/{fid}
POST   /api/v1/filters/
PATCH  /api/v1/filters/{fid}
DELETE /api/v1/filters/{fid}
```

### Rutas MT / MO
```
GET    /api/v1/mt-routes/             GET    /api/v1/mo-routes/
GET    /api/v1/mt-routes/{order}      GET    /api/v1/mo-routes/{order}
POST   /api/v1/mt-routes/             POST   /api/v1/mo-routes/
PATCH  /api/v1/mt-routes/{order}      PATCH  /api/v1/mo-routes/{order}
DELETE /api/v1/mt-routes/{order}      DELETE /api/v1/mo-routes/{order}
DELETE /api/v1/mt-routes/flush        DELETE /api/v1/mo-routes/flush
```

### Interceptores MT / MO
```
GET    /api/v1/mt-interceptors/        GET    /api/v1/mo-interceptors/
GET    /api/v1/mt-interceptors/{order} GET    /api/v1/mo-interceptors/{order}
POST   /api/v1/mt-interceptors/        POST   /api/v1/mo-interceptors/
PATCH  /api/v1/mt-interceptors/{order} PATCH  /api/v1/mo-interceptors/{order}
DELETE /api/v1/mt-interceptors/{order} DELETE /api/v1/mo-interceptors/{order}
DELETE /api/v1/mt-interceptors/flush   DELETE /api/v1/mo-interceptors/flush
```

### Stats (solo lectura)
```
GET    /api/v1/stats/
GET    /api/v1/stats/smpp-connectors/{cid}
GET    /api/v1/stats/users/{uid}
GET    /api/v1/stats/http-api
GET    /api/v1/stats/smpp-server-api
```

### SMPP Server
```
GET    /api/v1/smpp-server/    # Lee desde /etc/jasmin/jasmin.cfg
PATCH  /api/v1/smpp-server/    # No soportado — retorna 501
```

### Sistema
```
GET    /api/v1/system/session
POST   /api/v1/system/persist
POST   /api/v1/system/reload
POST   /api/v1/system/reconnect
```

### SMS
```
POST   /api/v1/sms/send
POST   /api/v1/sms/send/binary
GET    /api/v1/sms/rate?username=&password=&to=
GET    /api/v1/sms/balance?username=&password=
```

---

## Comportamiento de Persist

La API ejecuta `persist` automáticamente tras **cada operación de escritura exitosa**, garantizando que la configuración sobrevive reinicios de Jasmin. Si `persist` falla, la operación completa se considera fallida.

Para persistir manualmente o recargar desde disco:

```bash
POST /api/v1/system/persist   # Guarda en disco
POST /api/v1/system/reload    # Recarga desde disco
```

---

## Consideraciones de Producción

- **Jasmin jcli no es concurrente**: los comandos se serializan. Operaciones administrativas simultáneas se encolan.
- **SMPP Server no configurable via API**: `smppserver` no existe en jcli. La configuración está en `/etc/jasmin/jasmin.cfg` y requiere reinicio de Jasmin.
- **Scripts de interceptores persisten en disco**: al eliminar un interceptor, el archivo `.py` no se elimina automáticamente.
- **`filter --update` no existe**: `PATCH /filters/{fid}` hace delete + recrear internamente.
- **Filtros en respuestas de rutas**: Jasmin no expone FIDs en `route -s`. Las respuestas de GET siempre muestran `filters: []`.
- **Stats se resetean al reiniciar Jasmin**: no persisten entre reinicios.
- **DefaultRoute siempre en order 0**: Jasmin ignora el order enviado para DefaultRoute.

---

## Documentación de Módulos

Ver `docs/jasmin/` para documentación detallada por módulo:

- [README — Arquitectura y flujos](docs/jasmin/README.md)
- [Grupos](docs/jasmin/groups.md)
- [Usuarios](docs/jasmin/users.md)
- [Conectores SMPP](docs/jasmin/smpp-connectors.md)
- [Conectores HTTP](docs/jasmin/http-connectors.md)
- [Filtros](docs/jasmin/filters.md)
- [Rutas MT](docs/jasmin/mt-routes.md)
- [Rutas MO](docs/jasmin/mo-routes.md)
- [Interceptores MT](docs/jasmin/mt-interceptors.md)
- [Interceptores MO](docs/jasmin/mo-interceptors.md)
- [SMPP Server](docs/jasmin/smpp-server.md)
- [Estadísticas](docs/jasmin/stats.md)
- [Sistema](docs/jasmin/system.md)
- [SMS](docs/jasmin/sms.md)

---

## Tecnologías

- **Python 3.13+**
- **FastAPI** — Framework REST con sub-app mounting para API versioning
- **Pydantic v2** — Validación y schemas con documentación por campo
- **httpx** — Cliente HTTP async para proxy al API HTTP de Jasmin
- **slowapi** — Rate limiting
- **uv** — Gestor de paquetes
