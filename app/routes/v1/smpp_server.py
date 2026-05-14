from fastapi import APIRouter

from app.controllers.smpp_server_controller import SmppServerController
from app.schemas.smpp_server import SmppServerOut, SmppServerUpdate
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/smpp-server", tags=["SMPP Server"])


@router.get("/", response_model=ApiResponse[SmppServerOut], summary="Get SMPP server configuration")
async def get_smpp_server():
    """
    Returns the inbound SMPP server configuration read from `/etc/jasmin/jasmin.cfg`.

    The SMPP server is the endpoint that external SMPP clients (ESME) connect to
    in order to submit MT messages or receive MO messages via SMPP bind.

    > **Note:** This configuration is read-only via the API. Changing it requires
    > editing `/etc/jasmin/jasmin.cfg` directly and restarting Jasmin.
    > Uncommented values in the file override Jasmin defaults.

    **Response:**
    ```json
    {
      "data": {
        "host": "0.0.0.0",
        "port": 2775,
        "max_bindings": null
      }
    }
    ```

    **Response fields:**
    - `host` — bind address for the SMPP server (Jasmin default: `0.0.0.0`)
    - `port` — TCP port the SMPP server listens on (Jasmin default: `2775`)
    - `max_bindings` — maximum simultaneous SMPP sessions allowed (`null` = Jasmin default)
    """
    return success(data=await SmppServerController().get_config())


@router.patch("/", response_model=ApiResponse[SmppServerOut], summary="Update SMPP server configuration (not supported)")
async def update_smpp_server(body: SmppServerUpdate):
    """
    **Not supported.** Always returns HTTP 501.

    SMPP server settings (`host`, `port`, `max_bindings`) are configured via
    `/etc/jasmin/jasmin.cfg` and require a full Jasmin restart to take effect.
    They cannot be changed at runtime through jcli.

    To modify the SMPP server configuration:
    1. Edit `/etc/jasmin/jasmin.cfg` under the `[smpp-server]` section
    2. Restart the Jasmin service

    **Example `jasmin.cfg` section:**
    ```ini
    [smpp-server]
    port = 2775
    bind = 0.0.0.0
    ```
    """
    return success(data=await SmppServerController().update_config(body))
