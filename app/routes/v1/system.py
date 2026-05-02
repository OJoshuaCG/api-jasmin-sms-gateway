from fastapi import APIRouter

from app.controllers.system_controller import SystemController
from app.schemas.system import SessionOut
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/system", tags=["System"])


@router.post("/persist", response_model=ApiResponse[str])
async def persist():
    msg = await SystemController().persist()
    return success(data=msg)


@router.post("/reload", response_model=ApiResponse[str])
async def reload():
    msg = await SystemController().reload()
    return success(data=msg)


@router.post("/reconnect", response_model=ApiResponse[str])
async def reconnect():
    msg = await SystemController().reconnect()
    return success(data=msg)


@router.get("/session", response_model=ApiResponse[SessionOut])
async def session_info():
    return success(data=await SystemController().session_info())
