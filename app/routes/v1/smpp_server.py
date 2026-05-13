from fastapi import APIRouter

from app.controllers.smpp_server_controller import SmppServerController
from app.schemas.smpp_server import SmppServerOut, SmppServerUpdate
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/smpp-server", tags=["SMPP Server"])


@router.get(
    "/",
    response_model=ApiResponse[SmppServerOut],
    summary="Get SMPP server configuration",
    description=(
        "Returns the SMPP server configuration read from /etc/jasmin/jasmin.cfg. "
        "Uncommented values override Jasmin defaults (bind=0.0.0.0, port=2775)."
    ),
)
async def get_smpp_server():
    return success(data=await SmppServerController().get_config())


@router.patch(
    "/",
    response_model=ApiResponse[SmppServerOut],
    summary="Update SMPP server configuration (not supported)",
    description=(
        "Not supported. SMPP server settings are configured via /etc/jasmin/jasmin.cfg "
        "and require a Jasmin restart to take effect. Always returns 501."
    ),
)
async def update_smpp_server(body: SmppServerUpdate):
    return success(data=await SmppServerController().update_config(body))
