from fastapi import APIRouter

from app.controllers.smpp_server_controller import SmppServerController
from app.schemas.smpp_server import SmppServerOut
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


