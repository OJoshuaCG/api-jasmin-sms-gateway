# Formato Estándar de Respuestas

## El Envelope `ApiResponse[T]`

Todas las respuestas exitosas usan el mismo envelope. Los campos `None` se excluyen automáticamente del JSON.

```python
class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None           # Payload principal
    message: str | None = None      # Mensaje para el usuario final
    pagination: PaginationMeta | None = None  # Solo en respuestas paginadas
```

## Los 3 Helpers

### `success(data, message?)` — Respuesta con datos

```python
from app.utils.response import success, ApiResponse

@router.get("/{id}", response_model=ApiResponse[UserOut])
async def get_user(id: int):
    user = controller.get_user(id)
    return success(data=user)
    # → {"data": {"id": 1, "name": "John"}}

    return success(data=user, message="Usuario encontrado")
    # → {"data": {"id": 1, "name": "John"}, "message": "Usuario encontrado"}
```

### `paginated(data, total, pagination, message?)` — Lista paginada

```python
from app.utils.response import paginated, ApiResponse
from app.utils.pagination import PaginationDep

@router.get("/", response_model=ApiResponse[list[UserOut]])
async def list_users(pagination: PaginationDep):
    users = model.find_all(limit=pagination.size, offset=pagination.offset)
    total = model.count()
    return paginated(users, total=total, pagination=pagination)
```

Respuesta:
```json
{
  "data": [{"id": 1}, {"id": 2}],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

### `empty(message?)` — Sin contenido (DELETE, acciones void)

```python
from app.utils.response import empty, ApiResponse

@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_user(id: int):
    controller.delete_user(id)
    return empty("Usuario eliminado exitosamente")
    # → {"message": "Usuario eliminado exitosamente"}

    return empty()
    # → {}
```

## Formato de Errores

Los errores usan un formato independiente — **no se modifican con el envelope**. Salen del exception handler directamente:

```json
{"detail": {"msg": "Usuario no encontrado", "type": "AppHttpException"}}
{"detail": {"msg": "Error de validación en: email, age", "type": "RequestValidationError",
            "context": [{"field": "email", "msg": "..."}]}}
{"detail": {"msg": "Demasiadas solicitudes. Límite: 100 per 1 minute", "type": "RateLimitExceeded"}}
{"detail": {"msg": "Error interno del servidor", "type": "InternalServerError"}}
```

En `APP_ENV=development`, los errores incluyen `"context"` y `"loc"` con información técnica del error.

## OpenAPI / Swagger

Al usar `response_model=ApiResponse[UserOut]`, Swagger muestra el schema correcto y tipado de la respuesta. FastAPI **no aplica** `response_model` a las respuestas de exception handlers — no hay conflicto entre ambos formatos.

## Resumen de Salidas

| Situación | Salida JSON |
|---|---|
| `success(data=obj)` | `{"data": {...}}` |
| `success(data=obj, message="ok")` | `{"data": {...}, "message": "ok"}` |
| `paginated(items, total, pagination)` | `{"data": [...], "pagination": {...}}` |
| `empty("msg")` | `{"message": "msg"}` |
| `empty()` | `{}` |
| Error controlado | `{"detail": {"msg": "...", "type": "..."}}` |
