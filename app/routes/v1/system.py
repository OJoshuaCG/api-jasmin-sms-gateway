from fastapi import APIRouter

from app.controllers.system_controller import SystemController
from app.schemas.system import SessionOut
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/system", tags=["System"])


@router.post("/persist", response_model=ApiResponse[str], summary="Persist Jasmin configuration to disk")
async def persist():
    """
    Saves the current Jasmin in-memory configuration to disk.

    Jasmin holds its running configuration in memory. This command flushes it to
    the persistence storage (usually `/etc/jasmin/store/`). Without persisting,
    any changes made via jcli are lost when Jasmin restarts.

    > **Note:** All write operations through this API (create, update, delete)
    > call persist automatically. Use this endpoint only if you suspect the
    > on-disk state is out of sync with the in-memory state.

    **Response:**
    ```json
    { "data": "Persistence storage updated" }
    ```

    Returns **503** if the Jasmin Telnet session is not connected.
    """
    msg = await SystemController().persist()
    return success(data=msg)


@router.post("/reload", response_model=ApiResponse[str], summary="Reload Jasmin configuration from disk")
async def reload():
    """
    Reloads the Jasmin configuration from disk into memory, discarding
    any unsaved in-memory changes.

    Use this after manually editing Jasmin's configuration files
    (e.g. `/etc/jasmin/store/`) and wanting to apply the changes
    without restarting Jasmin.

    > **Warning:** Any in-memory changes not previously persisted will be lost.

    **Response:**
    ```json
    { "data": "Configuration reloaded successfully" }
    ```

    Returns **503** if the Jasmin Telnet session is not connected.
    """
    msg = await SystemController().reload()
    return success(data=msg)


@router.post("/reconnect", response_model=ApiResponse[str], summary="Reconnect the Telnet session")
async def reconnect():
    """
    Forces a reconnect of the API's persistent Telnet session to Jasmin's jcli.

    The API maintains a single persistent Telnet connection to Jasmin. If that
    connection drops (e.g. Jasmin restarted, network interruption), all admin
    endpoints will return 503. This endpoint triggers an immediate reconnect
    attempt instead of waiting for the automatic retry.

    **Response:**
    ```json
    { "data": "Reconnected successfully" }
    ```

    Returns **503** if reconnection fails (Jasmin is still unavailable).
    """
    msg = await SystemController().reconnect()
    return success(data=msg)


@router.get("/session", response_model=ApiResponse[SessionOut], summary="Get Telnet session info")
async def session_info():
    """
    Returns the current state of the API's persistent Telnet connection to Jasmin jcli.

    Use this to diagnose connectivity issues or verify that the API is properly
    connected to Jasmin before making admin requests.

    **Response:**
    ```json
    {
      "data": {
        "connected": true,
        "reconnecting": false,
        "uptime_seconds": 3600.5,
        "host": "127.0.0.1",
        "port": 8990
      }
    }
    ```

    **Response fields:**
    - `connected` — whether the Telnet session is currently active
    - `reconnecting` — whether an automatic reconnect is in progress
    - `uptime_seconds` — seconds since the session was established (`null` if not connected)
    - `host` — Jasmin Telnet host (from `JASMIN_TELNET_HOST` env var)
    - `port` — Jasmin Telnet port (from `JASMIN_TELNET_PORT` env var)
    """
    return success(data=await SystemController().session_info())
