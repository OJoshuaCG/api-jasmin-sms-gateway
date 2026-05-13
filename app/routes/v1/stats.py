from fastapi import APIRouter

from app.controllers.stats_controller import StatsController
from app.schemas.stats import (
    GlobalStatsOut,
    HttpApiStatsOut,
    SmppConnectorStatsOut,
    SmppServerApiStatsOut,
    UserStatsOut,
)
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/", response_model=ApiResponse[GlobalStatsOut])
async def get_global_stats():
    return success(data=await StatsController().get_global_stats())


@router.get("/smpp-connectors/{cid}", response_model=ApiResponse[SmppConnectorStatsOut])
async def get_smpp_connector_stats(cid: str):
    return success(data=await StatsController().get_smppccm_stats(cid))


@router.get("/users/{uid}", response_model=ApiResponse[UserStatsOut])
async def get_user_stats(uid: str):
    return success(data=await StatsController().get_user_stats(uid))


@router.get("/http-api", response_model=ApiResponse[HttpApiStatsOut])
async def get_httpapi_stats():
    return success(data=await StatsController().get_httpapi_stats())


@router.get("/smpp-server-api", response_model=ApiResponse[SmppServerApiStatsOut])
async def get_smppsapi_stats():
    return success(data=await StatsController().get_smppsapi_stats())
