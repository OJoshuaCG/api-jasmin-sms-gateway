from fastapi import APIRouter

from app.controllers.mo_routes_controller import MoRoutesController
from app.schemas.routes import MoRouteCreate, MoRouteOut, MoRouteUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mo-routes", tags=["MO Routes"])


@router.get("/", response_model=ApiResponse[list[MoRouteOut]], summary="List all MO routes")
async def list_routes():
    """
    Returns all MO (mobile-originated / inbound) routes ordered by priority.

    MO routes determine which HTTP connector receives an inbound SMS from the SMSC.
    Routes are evaluated in ascending order — the first whose filters match is used.
    `DefaultRoute` (order 0) is the fallback.

    **Response fields:**
    - `order` — evaluation priority (lower = higher priority)
    - `type` — route type: `DefaultRoute` or `StaticMORoute`
    - `connector` — HTTP connector ID with prefix (e.g. `http(webhook_crm)`)
    - `filters` — always `[]` in responses; Jasmin does not expose filter FIDs in route show output
    """
    return success(data=await MoRoutesController().list_routes())


@router.get("/{order}", response_model=ApiResponse[MoRouteOut], summary="Get a MO route")
async def get_route(order: int):
    """
    Returns a single MO route by its order (priority) number.

    **Path parameter:**
    - `order` — route priority number (e.g. `0` for DefaultRoute)

    Returns **404** if no route exists at that order.
    """
    return success(data=await MoRoutesController().get_route(order))


@router.post("/", response_model=ApiResponse[MoRouteOut], status_code=201, summary="Create a MO route")
async def create_route(body: MoRouteCreate):
    """
    Creates a new MO route.

    **Body examples:**

    `DefaultRoute` — catch-all fallback, no filters needed:
    ```json
    {
      "type": "DefaultRoute",
      "order": 0,
      "connector": "http(webhook_crm)"
    }
    ```

    `StaticMORoute` — route inbound messages from a specific connector:
    ```json
    {
      "type": "StaticMORoute",
      "order": 10,
      "connector": "http(webhook_support)",
      "filters": ["ft_short_code"]
    }
    ```

    **Field reference:**

    | Field | Required | Description |
    |---|---|---|
    | `type` | Yes | `DefaultRoute` or `StaticMORoute` |
    | `order` | Yes | Priority (0 = highest). `DefaultRoute` is always stored at 0 by Jasmin |
    | `connector` | Yes | HTTP connector ID prefixed with `http(...)` |
    | `filters` | No | Filter FIDs. Required for `StaticMORoute`. Empty = TransparentFilter |

    Returns **409** if a route already exists at the same order.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await MoRoutesController().create_route(body), message="MO route created")


@router.patch("/{order}", response_model=ApiResponse[MoRouteOut], summary="Update a MO route")
async def update_route(order: int, body: MoRouteUpdate):
    """
    Updates an existing MO route.

    > **Important:** Jasmin has no native route update command.
    > This endpoint **flushes all MO routes and recreates them** internally,
    > preserving the order of all other routes. The route at the given `order` is replaced.

    **Example — redirect inbound messages to a different webhook:**
    ```json
    {
      "connector": "http(webhook_v2)"
    }
    ```

    Omitted fields are carried over from the existing route.

    Returns **404** if no route exists at that order.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await MoRoutesController().update_route(order, body))


@router.delete("/flush", response_model=ApiResponse[None], summary="Flush all MO routes")
async def flush_routes():
    """
    Deletes **all** MO routes at once.

    > **Warning:** This is a destructive operation. All inbound routing rules are
    > removed immediately. Incoming messages will not be delivered until routes
    > are recreated.

    Configuration is automatically persisted to disk after flushing.
    """
    await MoRoutesController().flush_routes()
    return empty("All MO routes flushed")


@router.delete("/{order}", response_model=ApiResponse[None], summary="Delete a MO route")
async def delete_route(order: int):
    """
    Deletes a single MO route by its order number.

    **Path parameter:**
    - `order` — route priority number to delete (e.g. `10`)

    Returns **404** if no route exists at that order.

    Configuration is automatically persisted to disk after deletion.
    """
    await MoRoutesController().delete_route(order)
    return empty("MO route deleted")
