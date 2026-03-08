from fastapi import APIRouter

from app.routes.v1 import test

router = APIRouter()

router.include_router(test.router)
