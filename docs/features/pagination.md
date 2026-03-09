# Paginación

## Uso Básico

```python
from app.utils.pagination import PaginationDep
from app.utils.response import ApiResponse, paginated

@router.get("/users", response_model=ApiResponse[list[UserOut]])
async def list_users(pagination: PaginationDep):
    users = model.find_all(limit=pagination.size, offset=pagination.offset)
    total = model.count()
    return paginated(users, total=total, pagination=pagination)
```

Query params aceptados: `GET /api/v1/users?page=2&size=10`

## `PaginationParams` — Atributos Disponibles

| Atributo | Tipo | Descripción |
|---|---|---|
| `pagination.page` | `int` | Número de página (desde 1) |
| `pagination.size` | `int` | Items por página |
| `pagination.offset` | `int` | `(page - 1) * size` — listo para SQL `OFFSET` |

## Uso en SQL Directo

```python
def find_all(self, limit: int, offset: int) -> list[dict]:
    return self.db.execute_query(
        "SELECT * FROM users LIMIT :limit OFFSET :offset",
        {"limit": limit, "offset": offset},
        fetchone=False
    )

def count(self) -> int:
    result = self.db.execute_query(
        "SELECT COUNT(*) as total FROM users",
        fetchone=True
    )
    return result["total"]
```

## Configuración

| Variable | Default | Descripción |
|---|---|---|
| `PAGINATION_MAX_SIZE` | `50` | Máximo items/página. Hard cap en código: `200`. Si el valor supera 200, se usa 200. |

El developer puede reducir el límite en `.env` (ej: `PAGINATION_MAX_SIZE=20`) pero no puede superarlo sobre 200 por diseño.

## Respuesta Paginada

```json
{
  "data": [{"id": 1, "name": "..."}, {"id": 2, "name": "..."}],
  "pagination": {
    "page": 2,
    "size": 10,
    "total": 87,
    "pages": 9,
    "has_next": true,
    "has_prev": true
  }
}
```
