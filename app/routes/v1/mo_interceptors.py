from fastapi import APIRouter

from app.controllers.interceptors_controller import MoInterceptorsController
from app.schemas.interceptors import InterceptorOut, MoInterceptorCreate, MoInterceptorUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mo-interceptors", tags=["MO Interceptors"])


@router.get("/", response_model=ApiResponse[list[InterceptorOut]], summary="List all MO interceptors")
async def list_interceptors():
    """
    Returns all MO (mobile-originated / inbound) interceptors.

    MO interceptors run Python scripts on every inbound message **before routing**
    to an HTTP connector. They can inspect or modify message attributes, add tags,
    or reject messages. Multiple interceptors are evaluated in ascending order.

    **Response fields:**
    - `order` — evaluation priority (lower = evaluated first)
    - `type` — `DefaultInterceptor` (all messages) or `StaticMOInterceptor` (filtered)
    - `filters` — filter FIDs that must match (empty for `DefaultInterceptor`)
    - `script_path` — absolute path on disk where the Python script is stored

    > **Note:** Script files persist on disk even after deleting an interceptor.
    """
    return success(data=await MoInterceptorsController().list_interceptors())


@router.get("/{order}", response_model=ApiResponse[InterceptorOut], summary="Get a MO interceptor")
async def get_interceptor(order: int):
    """
    Returns a single MO interceptor by its order number.

    **Path parameter:**
    - `order` — interceptor priority number (e.g. `0`)

    Returns **404** if no interceptor exists at that order.
    """
    return success(data=await MoInterceptorsController().get_interceptor(order))


@router.post("/", response_model=ApiResponse[InterceptorOut], status_code=201, summary="Create a MO interceptor")
async def create_interceptor(body: MoInterceptorCreate):
    """
    Creates a new MO interceptor with a Python script.

    The script is saved to `JASMIN_SCRIPTS_DIR` (default: `/etc/jasmin/scripts`)
    and loaded by Jasmin at runtime. The `routable` object is injected into the
    script's namespace.

    **Script constraints:**
    - Must be a valid Python **module** (no bare `return` at module level)
    - Use `routable.reject()` to block an inbound message
    - Use `routable.pdu` to access SMPP PDU fields

    **Body examples:**

    `DefaultInterceptor` — pass-through (runs on all MO messages):
    ```json
    {
      "type": "DefaultInterceptor",
      "order": 0,
      "filters": [],
      "script": "# pass-through\\n"
    }
    ```

    `StaticMOInterceptor` — block inbound messages from a specific connector:
    ```json
    {
      "type": "StaticMOInterceptor",
      "order": 10,
      "filters": ["ft_conn_blocked"],
      "script": "routable.reject()\\n"
    }
    ```

    **Field reference:**

    | Field | Required | Description |
    |---|---|---|
    | `type` | Yes | `DefaultInterceptor` or `StaticMOInterceptor` |
    | `order` | Yes | Evaluation priority (0 = first) |
    | `filters` | No | Filter FIDs. Required for `StaticMOInterceptor`; ignored for `DefaultInterceptor` |
    | `script` | Yes | Valid Python module source code. Use `\\n` for newlines in JSON |

    Returns **409** if an interceptor already exists at the same order.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await MoInterceptorsController().create_interceptor(body), message="MO interceptor created")


@router.patch("/{order}", response_model=ApiResponse[InterceptorOut], summary="Update a MO interceptor")
async def update_interceptor(order: int, body: MoInterceptorUpdate):
    """
    Updates an existing MO interceptor.

    > **Important:** Jasmin has no native interceptor update command.
    > This endpoint **flushes all MO interceptors and recreates them** internally.

    **Example — replace the script:**
    ```json
    {
      "script": "routable.addTag(100)\\n"
    }
    ```

    Omitted fields are carried over from the existing interceptor.

    Returns **404** if no interceptor exists at that order.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await MoInterceptorsController().update_interceptor(order, body))


@router.delete("/flush", response_model=ApiResponse[None], summary="Flush all MO interceptors")
async def flush_interceptors():
    """
    Deletes **all** MO interceptors at once.

    > **Warning:** All inbound message interception rules are removed immediately.

    > Script files on disk are **not** deleted — only the Jasmin configuration entries
    > are removed.

    Configuration is automatically persisted to disk after flushing.
    """
    await MoInterceptorsController().flush_interceptors()
    return empty("All MO interceptors flushed")


@router.delete("/{order}", response_model=ApiResponse[None], summary="Delete a MO interceptor")
async def delete_interceptor(order: int):
    """
    Deletes a single MO interceptor by its order number.

    **Path parameter:**
    - `order` — interceptor priority number to delete

    > **Note:** The Python script file on disk is **not** deleted.

    Returns **404** if no interceptor exists at that order.

    Configuration is automatically persisted to disk after deletion.
    """
    await MoInterceptorsController().delete_interceptor(order)
    return empty("MO interceptor deleted")
