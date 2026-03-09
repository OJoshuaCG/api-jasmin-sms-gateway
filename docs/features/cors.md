# CORS

## Configuración

```env
CORS_ORIGINS=http://localhost:3000,https://myapp.com
```

La variable acepta orígenes separados por coma. Se parsea automáticamente en `environments.py`.

```env
# Desarrollo — permitir todos los orígenes
CORS_ORIGINS=*

# Producción — orígenes específicos
CORS_ORIGINS=https://myapp.com,https://admin.myapp.com,https://api.myapp.com
```

## Configuración Actual

```python
CORSMiddleware(
    allow_origins=CORS_ORIGINS,   # Desde variable de entorno
    allow_credentials=True,        # Permite cookies y headers de auth
    allow_methods=["*"],           # Todos los métodos HTTP
    allow_headers=["*"],           # Todos los headers
)
```

Para personalizar métodos u headers específicos, editar `create_versioned_app()` en `app/core/versioned_app.py`.

## Advertencia: `*` + `credentials=True`

Los browsers rechazan respuestas con `Access-Control-Allow-Origin: *` cuando la request incluye credenciales (cookies, `Authorization` header). Si tu frontend envía credenciales, **debes definir orígenes específicos**:

```env
# ❌ No funciona con credenciales en browser
CORS_ORIGINS=*

# ✓ Funciona con credenciales
CORS_ORIGINS=http://localhost:3000,https://myapp.com
```

## Posición en el Stack de Middlewares

CORS es el segundo middleware en ejecutarse (después de `RequestSizeMiddleware`). Esto permite que las requests `OPTIONS` de preflight sean respondidas inmediatamente, antes de que se procesen en middlewares más internos.

## CORS en `/health`

El endpoint `/health` está en el app principal, **no** en la sub-app versionada, por lo que no tiene `CORSMiddleware`. Si necesitas llamar `/health` desde un browser con CORS, agrega el middleware al app principal en `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware
from app.core.environments import CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```
