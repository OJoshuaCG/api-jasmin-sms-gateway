from fastapi import APIRouter, Depends

from app.core.api_key import require_api_key
from app.routes.v1 import (
    filters,
    groups,
    http_connectors,
    insights,
    mo_interceptors,
    mo_routes,
    mt_interceptors,
    mt_routes,
    smpp_connectors,
    smpp_server,
    sms,
    stats,
    system,
    test,
    users,
)

# All routes in this router require a valid X-API-Key header
router = APIRouter(dependencies=[Depends(require_api_key)])

router.include_router(groups.router)
router.include_router(users.router)
router.include_router(smpp_connectors.router)
router.include_router(http_connectors.router)
router.include_router(filters.router)
router.include_router(mt_routes.router)
router.include_router(mo_routes.router)
router.include_router(mt_interceptors.router)
router.include_router(mo_interceptors.router)
router.include_router(smpp_server.router)
router.include_router(stats.router)
router.include_router(system.router)
router.include_router(sms.router)
router.include_router(insights.router)
router.include_router(test.router)
