# FastAPI Template

> **Plantilla profesional de FastAPI lista para producción, con arquitectura MVC, versionado de API, seguridad, utilidades y mejores prácticas integradas.**

## Características

| Categoría | Funcionalidad |
|---|---|
| **Arquitectura** | Patrón MVC (Routes → Controllers → Models), API versionada por sub-apps |
| **Respuestas** | Envelope estándar (`ApiResponse[T]`) con helpers `success()`, `paginated()`, `empty()` |
| **Middlewares** | Context, Logger (configurable), CORS, Rate Limiting, Request Size |
| **Seguridad** | JWT (`JWTService`), cifrado Fernet (`CryptoService`), gestión de secretos |
| **Base de Datos** | SQLAlchemy 2.0, SQL directo, Stored Procedures, pool de conexiones |
| **Migraciones** | Alembic configurado y listo para usar |
| **Errores** | Handlers globales para `AppHttpException`, `RequestValidationError`, `RateLimitExceeded` |
| **Paginación** | `PaginationDep` inyectable con `Depends()`, respuesta estandarizada |
| **File Upload** | `save_upload()` / `save_uploads()` con validación de tipo y tamaño |
| **Logging** | Logger centralizado con trazabilidad por Request ID |
| **Configuración** | Variables de entorno centralizadas en `environments.py` |

---

## Inicio Rápido

### 1. Clonar y preparar

```bash
git clone <tu-repositorio>
cd fastapi-template

# Si inicias un proyecto nuevo desde esta plantilla:
rm -rf .git && git init
```

### 2. Instalar uv (gestor de paquetes)

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Instalar dependencias

```bash
uv sync
```

### 4. Configurar entorno

```bash
cp .env.example .env
```

Editar `.env` con tus valores (ver [Variables de Entorno](#variables-de-entorno)).

### 5. Ejecutar

```bash
# Desarrollo con hot-reload
uv run uvicorn main:app --reload

# Puerto específico
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### 6. Verificar

| URL | Descripción |
|---|---|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/api/v1/docs` | Swagger UI v1 |
| `http://localhost:8000/api/v1/redoc` | ReDoc v1 |
| `http://localhost:8000/api/v1/test/ping` | Endpoint de prueba |

---

## Variables de Entorno

Todas las variables se documentan en `.env.example`. A continuación el resumen completo:

```env
# ======= Application =======
APP_ENV=development          # development | production
APP_NAME="FastAPI Project"
SECRET_KEY=tu_clave_secreta  # python -c "import secrets; print(secrets.token_hex(32))"

# ======= Logger =======
LOGGER_LEVEL=INFO
LOGGER_MIDDLEWARE_ENABLED=True
LOGGER_MIDDLEWARE_SHOW_HEADERS=False
LOGGER_MIDDLEWARE_SHOW_QUERY_PARAMS=True
LOGGER_MIDDLEWARE_SHOW_BODY=True
LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS=True   # False = reemplaza URL con template de ruta
LOGGER_EXCEPTIONS_ENABLED=False

# ======= Docs =======
DOCS_ENABLED=True            # False = desactiva /docs, /redoc y /openapi.json

# ======= Rate Limiting =======
RATE_LIMIT_DEFAULT=100/minute  # second | minute | hour | day

# ======= Pagination =======
PAGINATION_MAX_SIZE=50       # Máximo items/página. Hard cap en código: 200.

# ======= Request Size =======
REQUEST_MAX_SIZE_MB=10       # Aplica a POST, PUT, PATCH

# ======= CORS =======
CORS_ORIGINS=*               # Separados por coma. Nota: * + credentials no funciona en browsers.

# ======= Database =======
DB_HOST=localhost
DB_USER=username
DB_PASS=password
DB_NAME=database
DB_PORT=3306
DB_ENGINE=sqlite             # sqlite | mysql+pymysql | postgresql+psycopg2
```

---

## Estructura del Proyecto

```
fastapi-template/
├── app/
│   ├── core/
│   │   ├── context.py          # ContextVars de request (Request ID, IP, método, etc.)
│   │   ├── database.py         # Clase Database (SQL directo, ORM, Stored Procedures)
│   │   ├── environments.py     # Todas las variables de entorno centralizadas
│   │   ├── limiter.py          # Singleton de slowapi Limiter (rate limiting)
│   │   ├── logger.py           # get_logger() centralizado
│   │   └── versioned_app.py    # Factory create_versioned_app() para sub-apps versionadas
│   ├── controllers/
│   │   └── user_controller.py  # Ejemplo de controller (CRUD de usuarios)
│   ├── exceptions/
│   │   ├── AppHttpException.py     # Excepción HTTP personalizada con tracking
│   │   ├── HandlerExceptions.py    # Handlers globales (App, Validation, RateLimit, Generic)
│   │   └── __init__.py
│   ├── middleware/
│   │   ├── ContextMiddleware.py    # Genera Request ID, establece ContextVars
│   │   ├── LoggerMiddleware.py     # Logging de requests/responses
│   │   └── RequestSizeMiddleware.py # Valida tamaño máximo de body
│   ├── models/
│   │   ├── base.py             # DeclarativeBase, TimestampMixin (SQLAlchemy 2.0)
│   │   ├── user.py             # Modelo ORM de ejemplo (para Alembic)
│   │   ├── user_model.py       # Modelo de datos SQL directo (para MVC)
│   │   └── __init__.py         # CRÍTICO: exportar modelos para Alembic
│   ├── routes/
│   │   ├── health.py           # GET /health (sin versión, sin rate limiting)
│   │   └── v1/
│   │       ├── routes.py       # Agregador de rutas v1
│   │       └── test.py         # Endpoints de ejemplo y testing
│   ├── security/
│   │   ├── crypto.py           # CryptoService (Fernet — cifrado reversible)
│   │   ├── jwt_service.py      # JWTService (crear y verificar tokens)
│   │   └── secrets.py          # SecretManager (generar y derivar claves)
│   └── utils/
│       ├── dict_utils.py       # _sanitize_dict() (uso interno)
│       ├── file_upload.py      # save_upload() / save_uploads()
│       ├── pagination.py       # PaginationParams, PaginationDep
│       └── response.py         # ApiResponse[T], success(), paginated(), empty()
├── uploads/                    # Archivos temporales (ignorado por git, excepto .gitkeep)
├── alembic/                    # Migraciones de base de datos
├── docs/                       # Documentación detallada
├── main.py                     # Punto de entrada: monta sub-apps y /health
├── pyproject.toml
└── .env.example
```

---

## Arquitectura: API Versionada

Cada versión de la API es una **sub-aplicación FastAPI independiente** con sus propios middlewares, handlers y documentación.

```
main.py
├── GET /health              ← sin versión, sin rate limiting
└── /api/v1  ←──────────────── v1_app (create_versioned_app("v1"))
    ├── GET  /docs           ← Swagger de v1
    ├── GET  /redoc          ← ReDoc de v1
    └── /test/...            ← rutas de negocio v1
```

### Agregar v2

```python
# main.py
from app.routes.v2.routes import router as v2_router

v2_app = create_versioned_app("v2")
v2_app.include_router(v2_router)
app.mount("/api/v2", v2_app)
```

Crear `app/routes/v2/routes.py` con los nuevos routers. Las rutas v1 no se afectan.

---

## Patrones de Uso

### Respuestas Estándar

```python
from app.utils.response import ApiResponse, success, paginated, empty

# Respuesta simple
@router.get("/{id}", response_model=ApiResponse[UserOut])
async def get_user(id: int):
    user = controller.get_user(id)
    return success(data=user)

# Con mensaje
    return success(data=user, message="Usuario creado exitosamente")

# Paginada
@router.get("/", response_model=ApiResponse[list[UserOut]])
async def list_users(pagination: PaginationDep):
    users = model.find_all(limit=pagination.size, offset=pagination.offset)
    total = model.count()
    return paginated(users, total=total, pagination=pagination)

# Sin contenido (DELETE)
@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_user(id: int):
    controller.delete_user(id)
    return empty("Usuario eliminado exitosamente")
```

**Formato de respuesta exitosa:**
```json
{"data": {"id": 1, "name": "John"}}
{"data": [...], "pagination": {"page": 1, "size": 20, "total": 150, "pages": 8, "has_next": true, "has_prev": false}}
{"message": "Usuario eliminado exitosamente"}
```

**Formato de error** (independiente del envelope):
```json
{"detail": {"msg": "Usuario no encontrado", "type": "AppHttpException"}}
{"detail": {"msg": "Error de validación en: email, age", "type": "RequestValidationError"}}
{"detail": {"msg": "Demasiadas solicitudes. Límite: 100 per 1 minute", "type": "RateLimitExceeded"}}
```

### Paginación

```python
from app.utils.pagination import PaginationDep
from app.utils.response import ApiResponse, paginated

@router.get("/users", response_model=ApiResponse[list[dict]])
async def list_users(pagination: PaginationDep):
    # pagination.page   → número de página (desde 1)
    # pagination.size   → items por página
    # pagination.offset → listo para SQL: LIMIT size OFFSET offset
    users = model.find_all(limit=pagination.size, offset=pagination.offset)
    total = model.count()
    return paginated(users, total=total, pagination=pagination)
```

Query params: `GET /users?page=2&size=10`

### File Upload

```python
from fastapi import File, UploadFile
from pathlib import Path
from app.utils.file_upload import save_upload, save_uploads
from app.utils.response import ApiResponse, success

@router.post("/avatar", response_model=ApiResponse[dict])
async def upload_avatar(file: UploadFile = File(...)):
    file_info = await save_upload(
        file,
        allowed_types=["image/jpeg", "image/png", "image/webp"],
        max_size_mb=2,
    )
    file_path = Path(file_info["path"])
    try:
        content = file_path.read_bytes()
        # Subir a S3, procesar imagen, etc.
        return success(data={"url": "..."}, message="Avatar actualizado")
    finally:
        if file_path.exists():
            file_path.unlink()  # Siempre eliminar el temporal
```

### Excepciones

```python
from app.exceptions import AppHttpException

raise AppHttpException(
    message="Usuario no encontrado",
    status_code=404,
    context={"user_id": user_id}  # Solo visible en APP_ENV=development
)
```

### Rate Limiting por Ruta

```python
from fastapi import Request
from app.core.limiter import limiter

@router.post("/login")
@limiter.limit("5/minute")          # Límite específico para este endpoint
async def login(request: Request):  # request es requerido por slowapi
    ...
```

### Context (Request ID, IP, etc.)

```python
from app.core.context import current_http_identifier, current_request_ip

request_id = current_http_identifier.get()
client_ip  = current_request_ip.get()
```

---

## Flujo de una Request

```
Cliente
  ↓
RequestSizeMiddleware  → rechaza si body > REQUEST_MAX_SIZE_MB (POST/PUT/PATCH)
  ↓
CORSMiddleware         → agrega headers CORS, maneja preflight OPTIONS
  ↓
ContextMiddleware      → genera Request ID, establece ContextVars
  ↓
LoggerMiddleware       → inicia timer, loguea request
  ↓
SlowAPIMiddleware      → verifica rate limit por IP
  ↓
ExceptionMiddleware    → captura excepciones → handlers → JSONResponse
  ↓
Endpoint               → Controller → Model → Database
  ↓
(respuesta sube por el mismo stack en orden inverso)
  ↓
LoggerMiddleware       → loguea response (status, duración)
  ↓
ContextMiddleware      → inyecta X-Request-ID en headers, limpia contexto
  ↓
Cliente recibe respuesta con header X-Request-ID
```

---

## Comandos de Referencia

```bash
# Desarrollo
uv run uvicorn main:app --reload
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Dependencias
uv add <paquete>
uv add --group dev <paquete>
uv remove <paquete>
uv sync

# Migraciones
uv run alembic revision --autogenerate -m "descripción"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic current
uv run alembic history
```

---

## Documentación

- [Inicio Rápido](docs/getting-started.md)
- [Estructura del Proyecto](docs/project-structure.md)
- [API Versionada](docs/features/api-versioning.md)
- [Respuestas Estándar](docs/features/response-format.md)
- [Paginación](docs/features/pagination.md)
- [File Upload](docs/features/file-upload.md)
- [Rate Limiting](docs/features/rate-limiting.md)
- [CORS](docs/features/cors.md)
- [Middlewares](docs/features/middlewares.md)
- [Sistema de Logging](docs/features/logging.md)
- [Manejo de Excepciones](docs/features/exceptions.md)
- [Base de Datos](docs/features/database.md)
- [Migraciones](README_MIGRATIONS.md)

## Tecnologías

- **[FastAPI](https://fastapi.tiangolo.com/)** — Framework web moderno y rápido
- **[SQLAlchemy 2.0](https://docs.sqlalchemy.org/)** — ORM y SQL toolkit
- **[Alembic](https://alembic.sqlalchemy.org/)** — Migraciones de base de datos
- **[Pydantic v2](https://docs.pydantic.dev/)** — Validación de datos y schemas
- **[slowapi](https://github.com/laurentS/slowapi)** — Rate limiting para Starlette/FastAPI
- **[uv](https://github.com/astral-sh/uv)** — Gestor de paquetes ultrarrápido
- **[Ruff](https://docs.astral.sh/ruff/)** — Linter y formateador extremadamente rápido
- **Python 3.13+**
