from fastapi import APIRouter

from app.controllers.stats_controller import StatsController
from app.schemas.stats import SmppConnectorStatsOut, UserStatsOut
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/", response_model=ApiResponse[dict])
async def get_global_stats():
    return success(data=await StatsController().get_global_stats())


@router.get("/smpp-connectors/{cid}", response_model=ApiResponse[SmppConnectorStatsOut])
async def get_smppccm_stats(cid: str):
    return success(data=await StatsController().get_smppccm_stats(cid))


@router.get("/users/{uid}", response_model=ApiResponse[UserStatsOut])
async def get_user_stats(uid: str):
    return success(data=await StatsController().get_user_stats(uid))
