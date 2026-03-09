# Estructura del Proyecto

## Vista General

```
fastapi-template/
├── app/
│   ├── core/
│   │   ├── context.py              # ContextVars para estado de request
│   │   ├── database.py             # Clase Database (SQL directo, ORM, SPs)
│   │   ├── environments.py         # Todas las variables de entorno
│   │   ├── limiter.py              # Singleton Limiter (rate limiting)
│   │   ├── logger.py               # get_logger() centralizado
│   │   └── versioned_app.py        # Factory create_versioned_app()
│   ├── controllers/
│   │   └── user_controller.py      # Ejemplo: CRUD de usuarios
│   ├── exceptions/
│   │   ├── AppHttpException.py     # Excepción HTTP personalizada
│   │   ├── HandlerExceptions.py    # Handlers globales de excepciones
│   │   └── __init__.py
│   ├── middleware/
│   │   ├── ContextMiddleware.py    # Request ID + ContextVars
│   │   ├── LoggerMiddleware.py     # Logging de requests/responses
│   │   └── RequestSizeMiddleware.py # Límite de tamaño de body
│   ├── models/
│   │   ├── base.py                 # DeclarativeBase + TimestampMixin
│   │   ├── user.py                 # Modelo ORM (para Alembic)
│   │   ├── user_model.py           # Modelo de datos SQL directo (MVC)
│   │   └── __init__.py             # CRÍTICO: exportar modelos ORM
│   ├── routes/
│   │   ├── health.py               # GET /health
│   │   └── v1/
│   │       ├── routes.py           # Agregador de rutas v1
│   │       └── test.py             # Endpoints de ejemplo
│   ├── security/
│   │   ├── crypto.py               # CryptoService (Fernet)
│   │   ├── jwt_service.py          # JWTService
│   │   └── secrets.py              # SecretManager
│   └── utils/
│       ├── dict_utils.py           # _sanitize_dict() (uso interno)
│       ├── file_upload.py          # save_upload() / save_uploads()
│       ├── pagination.py           # PaginationParams, PaginationDep
│       └── response.py             # ApiResponse[T], success(), paginated(), empty()
├── uploads/                        # Archivos temporales de upload (no versionado)
├── alembic/
│   ├── versions/                   # Archivos de migración
│   └── env.py                      # Configuración de Alembic
├── docs/                           # Documentación
├── main.py                         # Punto de entrada
├── pyproject.toml
├── .env.example
└── CLAUDE.md                       # Guía para agentes de IA
```

---

## Patrón de Arquitectura: MVC sin Vista

```
Request → Routes → Controllers → Models → Database
                       ↑               ↓
                  Exceptions        Response
```

- **Routes** (`app/routes/v1/`): Reciben requests, validan con Pydantic, delegan a controllers, retornan `ApiResponse`
- **Controllers** (`app/controllers/`): Lógica de negocio, validaciones, orquestación
- **Models** (`app/models/`): Interacción con base de datos

---

## Descripción de Componentes

### `app/core/`

| Archivo | Propósito |
|---|---|
| `environments.py` | Fuente única de verdad para variables de entorno. **Todo import de env vars debe venir de aquí.** |
| `database.py` | Clase `Database` con pool de conexiones, SQL directo y ORM |
| `context.py` | ContextVars accesibles desde cualquier punto del código durante una request |
| `logger.py` | `get_logger(name, level)` — retorna logger sin handlers duplicados |
| `limiter.py` | Instancia singleton de `slowapi.Limiter` compartida entre versiones |
| `versioned_app.py` | `create_versioned_app(version)` — factory que crea sub-apps con toda la configuración |

### `app/middleware/`

El orden de ejecución (de exterior a interior) es:

```
RequestSizeMiddleware → CORSMiddleware → ContextMiddleware → LoggerMiddleware → SlowAPIMiddleware
```

| Middleware | Cuándo ejecuta | Qué hace |
|---|---|---|
| `RequestSizeMiddleware` | Primero | Rechaza requests > `REQUEST_MAX_SIZE_MB` |
| `CORSMiddleware` | Segundo | Headers CORS, preflight OPTIONS |
| `ContextMiddleware` | Tercero | Genera Request ID, establece ContextVars |
| `LoggerMiddleware` | Cuarto | Loguea request + response con timing |
| `SlowAPIMiddleware` | Último | Verifica rate limit por IP |

### `app/exceptions/`

Tres handlers registrados en cada sub-app versionada:

| Handler | Tipo de excepción | Status |
|---|---|---|
| `app_exception_handler` | `AppHttpException` | El que defina el developer |
| `validation_exception_handler` | `RequestValidationError` (Pydantic) | 422 |
| `rate_limit_handler` | `RateLimitExceeded` (slowapi) | 429 |
| `generic_exception_handler` | Cualquier `Exception` no capturada | 500 |

Formato de respuesta de error (consistente en todos):
```json
{"detail": {"msg": "...", "type": "NombreDeLaExcepcion"}}
```
En `APP_ENV=development` se agrega `"context": {...}` con detalles técnicos.

### `app/utils/`

| Archivo | Exports principales | Uso |
|---|---|---|
| `response.py` | `ApiResponse[T]`, `success()`, `paginated()`, `empty()` | Retornar respuestas en endpoints |
| `pagination.py` | `PaginationDep`, `PaginationParams` | Inyectar con `Depends()` en endpoints |
| `file_upload.py` | `save_upload()`, `save_uploads()` | Guardar archivos subidos en `uploads/` |
| `dict_utils.py` | `_sanitize_dict()` | Uso interno en `database.py` |

### `app/security/`

| Archivo | Clase | Uso |
|---|---|---|
| `jwt_service.py` | `JWTService` | Crear y verificar JWT tokens |
| `crypto.py` | `CryptoService` | Cifrado/descifrado con Fernet (reversible) |
| `secrets.py` | `SecretManager` | Generar y derivar claves secretas |

### `app/routes/`

```
routes/
├── health.py       → GET /health  (en main app, sin versión)
└── v1/
    ├── routes.py   → Agrega todos los routers de v1
    └── test.py     → Endpoints de ejemplo y testing
```

Para agregar nuevos endpoints en v1:
1. Crear `app/routes/v1/mi_recurso.py`
2. Importarlo en `app/routes/v1/routes.py`

Para agregar v2:
1. Crear `app/routes/v2/` con su propia estructura
2. En `main.py`, descomentar las 3 líneas de v2

### `app/models/`

Dos tipos de archivos con propósitos distintos:

**`user.py`** — Modelo ORM (solo para Alembic/migraciones):
```python
class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
```

**`user_model.py`** — Modelo de datos SQL directo (para MVC):
```python
class UserModel:
    def find_by_id(self, user_id: int):
        return self.db.execute_query("SELECT * FROM users WHERE id = :id",
                                     {"id": user_id}, fetchone=True)
```

**`__init__.py`** — CRÍTICO: solo importar modelos ORM aquí:
```python
from app.models.base import Base, TimestampMixin
from app.models.user import User
__all__ = ["Base", "TimestampMixin", "User"]
```

---

## `main.py` — Punto de Entrada

```python
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(health_router)          # /health sin versión

v1_app = create_versioned_app("v1")       # Sub-app con todos los middlewares
v1_app.include_router(v1_router)
app.mount("/api/v1", v1_app)              # Docs en /api/v1/docs
```

`create_versioned_app()` configura automáticamente: CORS, Context, Logger, RequestSize, RateLimit, y todos los exception handlers.

---

## Convenciones de Nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos Python | `snake_case.py` | `user_model.py` |
| Clases | `PascalCase` | `UserController`, `ContextMiddleware` |
| Funciones/variables | `snake_case` | `get_user()`, `user_id` |
| Constantes / env vars | `UPPER_SNAKE_CASE` | `DB_HOST`, `RATE_LIMIT_DEFAULT` |
| Tablas SQL | plural `snake_case` | `users`, `blog_posts` |
| Endpoints API | plural `kebab-case` | `/users`, `/blog-posts` |

---

## Reglas Importantes

1. **Variables de entorno** → siempre importar desde `app.core.environments`, nunca `os.getenv()` directo
2. **Modelos ORM** → siempre registrarlos en `app/models/__init__.py` para que Alembic los detecte
3. **Nuevos middlewares** → agregarlos en `create_versioned_app()` de `versioned_app.py`
4. **Nuevos exception handlers** → registrarlos en `create_versioned_app()` Y en el handler del main app
5. **Archivos en `uploads/`** → siempre eliminarlos con `file_path.unlink()` después de procesarlos
