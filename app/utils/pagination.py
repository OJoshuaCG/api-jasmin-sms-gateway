import math
from typing import Annotated, Any

from fastapi import Depends, Query

from app.core.environments import PAGINATION_MAX_SIZE

# Tamaño por defecto cuando el cliente no especifica ?size=
_DEFAULT_SIZE = 20


class PaginationParams:
    """
    Dependencia de paginación reutilizable en cualquier endpoint.

    Uso en un route:
        from app.utils.pagination import PaginationDep, paginate

        @router.get("/users")
        async def list_users(pagination: PaginationDep):
            users = user_model.find_all(
                limit=pagination.size,
                offset=pagination.offset,
            )
            total = user_model.count()
            return paginate(users, total=total, pagination=pagination)

    Query params aceptados:
        ?page=1&size=20
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número de página (inicia en 1)"),
        size: int = Query(
            _DEFAULT_SIZE,
            ge=1,
            le=PAGINATION_MAX_SIZE,
            description=f"Elementos por página (máximo {PAGINATION_MAX_SIZE})",
        ),
    ):
        self.page = page
        self.size = size
        # offset listo para usar directamente en SQL: LIMIT size OFFSET offset
        self.offset: int = (page - 1) * size


# Alias de tipo para usar en signatures de endpoints
PaginationDep = Annotated[PaginationParams, Depends(PaginationParams)]


def paginate(
    data: list[Any],
    total: int,
    pagination: PaginationParams,
) -> dict:
    """
    Construye la respuesta paginada estándar.

    Args:
        data:       Lista de elementos de la página actual.
        total:      Total de registros (resultado de COUNT en BD).
        pagination: Instancia de PaginationParams obtenida via Depends.

    Returns:
        Dict con 'data' y 'pagination' meta.

    Ejemplo de respuesta:
        {
            "data": [...],
            "pagination": {
                "page": 1,
                "size": 20,
                "total": 150,
                "pages": 8,
                "has_next": true,
                "has_prev": false
            }
        }
    """
    pages = math.ceil(total / pagination.size) if total > 0 else 0

    return {
        "data": data,
        "pagination": {
            "page": pagination.page,
            "size": pagination.size,
            "total": total,
            "pages": pages,
            "has_next": pagination.page < pages,
            "has_prev": pagination.page > 1,
        },
    }
