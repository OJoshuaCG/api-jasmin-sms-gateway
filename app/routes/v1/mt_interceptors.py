from fastapi import APIRouter

from app.controllers.interceptors_controller import MtInterceptorsController
from app.schemas.interceptors import InterceptorOut, MtInterceptorCreate, MtInterceptorUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mt-interceptors", tags=["MT Interceptors"])


@router.get("/", response_model=ApiResponse[list[InterceptorOut]], summary="List all MT interceptors")
async def list_interceptors():
    """
    Returns all MT (mobile-terminated / outbound) interceptors.

    Interceptors run Python scripts on every outbound message **before routing**.
    They can inspect or modify message attributes, add tags, or reject messages.
    Multiple interceptors are evaluated in ascending order — all matching ones run.

    **Response fields:**
    - `order` — evaluation priority (lower = evaluated first)
    - `type` — `DefaultInterceptor` (all messages) or `StaticMTInterceptor` (filtered)
    - `filters` — filter FIDs that must match (empty for `DefaultInterceptor`)
    - `script_path` — absolute path on disk where the Python script is stored

    > **Note:** Script files persist on disk even after deleting an interceptor.
    > They are not automatically removed.
    """
    return success(data=await MtInterceptorsController().list_interceptors())


@router.get("/{order}", response_model=ApiResponse[InterceptorOut], summary="Get an MT interceptor")
async def get_interceptor(order: int):
    """
    Returns a single MT interceptor by its order number.

    **Path parameter:**
    - `order` — interceptor priority number (e.g. `0`)

    Returns **404** if no interceptor exists at that order.
    """
    return success(data=await MtInterceptorsController().get_interceptor(order))


@router.post("/", response_model=ApiResponse[InterceptorOut], status_code=201, summary="Create an MT interceptor")
async def create_interceptor(body: MtInterceptorCreate):
    """
    Creates a new MT interceptor with a Python script.

    The script is saved to `JASMIN_SCRIPTS_DIR` (default: `/etc/jasmin/scripts`)
    and loaded by Jasmin at runtime. The `routable` object is injected into the
    script's namespace by Jasmin.

    **Script constraints:**
    - Must be a valid Python **module** (no bare `return` at module level)
    - Use `routable.reject()` to block a message
    - Use `routable.pdu` to access SMPP PDU fields

    **Body examples:**

    `DefaultInterceptor` — pass-through (runs on all MT messages):
    ```json
    {
      "type": "DefaultInterceptor",
      "order": 0,
      "filters": [],
      "script": "# pass-through\\n"
    }
    ```

    `StaticMTInterceptor` — reject messages from a specific user:
    ```json
    {
      "type": "StaticMTInterceptor",
      "order": 10,
      "filters": ["ft_user_blocked"],
      "script": "routable.reject()\\n"
    }
    ```

    `StaticMTInterceptor` — add a tag to messages from Kenya numbers:
    ```json
    {
      "type": "StaticMTInterceptor",
      "order": 5,
      "filters": ["ft_src_ke"],
      "script": "routable.addTag(254)\\n"
    }
    ```

    **Field reference:**

    | Field | Required | Description |
    |---|---|---|
    | `type` | Yes | `DefaultInterceptor` or `StaticMTInterceptor` |
    | `order` | Yes | Evaluation priority (0 = first) |
    | `filters` | No | Filter FIDs. Required for `StaticMTInterceptor`; ignored for `DefaultInterceptor` |
    | `script` | Yes | Valid Python module source code. Use `\\n` for newlines in JSON |

    Returns **409** if an interceptor already exists at the same order.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await MtInterceptorsController().create_interceptor(body), message="MT interceptor created")


@router.patch("/{order}", response_model=ApiResponse[InterceptorOut], summary="Update an MT interceptor")
async def update_interceptor(order: int, body: MtInterceptorUpdate):
    """
    Updates an existing MT interceptor.

    > **Important:** Jasmin has no native interceptor update command.
    > This endpoint **flushes all MT interceptors and recreates them** internally.

    **Example — replace the script:**
    ```json
    {
      "script": "routable.addTag(999)\\n"
    }
    ```

    **Example — update filters only (reuse existing script on disk):**
    ```json
    {
      "filters": ["ft_user_premium"]
    }
    ```

    Omitted fields are carried over from the existing interceptor.

    Returns **404** if no interceptor exists at that order.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await MtInterceptorsController().update_interceptor(order, body))


@router.delete("/flush", response_model=ApiResponse[None], summary="Flush all MT interceptors")
async def flush_interceptors():
    """
    Deletes **all** MT interceptors at once.

    > **Warning:** This is a destructive operation. All outbound message interception
    > rules are removed immediately.

    > Script files on disk are **not** deleted — only the Jasmin configuration entries
    > are removed.

    Configuration is automatically persisted to disk after flushing.
    """
    await MtInterceptorsController().flush_interceptors()
    return empty("All MT interceptors flushed")


@router.delete("/{order}", response_model=ApiResponse[None], summary="Delete an MT interceptor")
async def delete_interceptor(order: int):
    """
    Deletes a single MT interceptor by its order number.

    **Path parameter:**
    - `order` — interceptor priority number to delete

    > **Note:** The Python script file on disk is **not** deleted.

    Returns **404** if no interceptor exists at that order.

    Configuration is automatically persisted to disk after deletion.
    """
    await MtInterceptorsController().delete_interceptor(order)
    return empty("MT interceptor deleted")
