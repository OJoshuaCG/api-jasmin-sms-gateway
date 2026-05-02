from fastapi import APIRouter

from app.controllers.smpp_server_controller import SmppServerController
from app.schemas.smpp_server import SmppServerOut, SmppServerUpdate
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/smpp-server", tags=["SMPP Server"])


@router.get("/", response_model=ApiResponse[SmppServerOut])
async def get_smpp_server():
    return success(data=await SmppServerController().get_config())


@router.patch("/", response_model=ApiResponse[SmppServerOut])
async def update_smpp_server(body: SmppServerUpdate):
    return success(data=await SmppServerController().update_config(body))
