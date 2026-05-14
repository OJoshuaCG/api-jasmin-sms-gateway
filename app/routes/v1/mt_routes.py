from fastapi import APIRouter

from app.controllers.mt_routes_controller import MtRoutesController
from app.schemas.routes import MtRouteCreate, MtRouteOut, MtRouteUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mt-routes", tags=["MT Routes"])


@router.get("/", response_model=ApiResponse[list[MtRouteOut]], summary="List all MT routes")
async def list_routes():
    """
    Returns all MT (mobile-terminated / outbound) routes ordered by priority.

    MT routes determine which SMPP connector Jasmin uses to deliver an outbound
    message. Routes are evaluated in ascending order — the first one whose filters
    match the message is used. `DefaultRoute` (order 0) is the fallback if no
    other route matches.

    **Response fields:**
    - `order` — evaluation priority (lower = higher priority)
    - `type` — route type: `DefaultRoute`, `StaticMTRoute`, `RandomRoundrobinMTRoute`
    - `connectors` — list of SMPP connector IDs with prefix (e.g. `smppc(carrier_mx)`)
    - `filters` — always `[]` in responses; Jasmin does not expose filter FIDs in route show output
    - `rate` — per-message cost charged to the user's balance (`null` = free)
    """
    return success(data=await MtRoutesController().list_routes())


@router.get("/{order}", response_model=ApiResponse[MtRouteOut], summary="Get an MT route")
async def get_route(order: int):
    """
    Returns a single MT route by its order (priority) number.

    **Path parameter:**
    - `order` — route priority number (e.g. `0` for DefaultRoute, `10` for a specific route)

    Returns **404** if no route exists at that order.
    """
    return success(data=await MtRoutesController().get_route(order))


@router.post("/", response_model=ApiResponse[MtRouteOut], status_code=201, summary="Create an MT route")
async def create_route(body: MtRouteCreate):
    """
    Creates a new MT route.

    **Body examples:**

    `DefaultRoute` — fallback for all messages, no filters needed:
    ```json
    {
      "type": "DefaultRoute",
      "order": 0,
      "connectors": ["smppc(carrier_mx)"],
      "rate": 0.05
    }
    ```

    `StaticMTRoute` — matches a specific user or condition:
    ```json
    {
      "type": "StaticMTRoute",
      "order": 10,
      "connectors": ["smppc(carrier_premium)"],
      "filters": ["ft_user_premium"],
      "rate": 0.03
    }
    ```

    `RandomRoundrobinMTRoute` — distributes load across multiple carriers:
    ```json
    {
      "type": "RandomRoundrobinMTRoute",
      "order": 5,
      "connectors": ["smppc(carrier_a)", "smppc(carrier_b)"],
      "filters": ["ft_all"],
      "rate": null
    }
    ```

    **Field reference:**

    | Field | Required | Description |
    |---|---|---|
    | `type` | Yes | `DefaultRoute` · `StaticMTRoute` · `RandomRoundrobinMTRoute` |
    | `order` | Yes | Priority (0 = highest). `DefaultRoute` is always stored at 0 by Jasmin |
    | `connectors` | Yes | SMPP connector IDs prefixed with `smppc(...)` |
    | `filters` | No | Filter FIDs to match. Required for `StaticMTRoute`. Empty = TransparentFilter |
    | `rate` | No | Per-message cost (default: `0.0` = free) |

    Returns **409** if a route already exists at the same order.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await MtRoutesController().create_route(body), message="MT route created")


@router.patch("/{order}", response_model=ApiResponse[MtRouteOut], summary="Update an MT route")
async def update_route(order: int, body: MtRouteUpdate):
    """
    Updates an existing MT route.

    > **Important:** Jasmin has no native route update command.
    > This endpoint **flushes all MT routes and recreates them** internally,
    > preserving the order of all other routes. The route at the given `order` is replaced.

    **Example — change connector and rate:**
    ```json
    {
      "connectors": ["smppc(carrier_backup)"],
      "rate": 0.08
    }
    ```

    Omitted fields are carried over from the existing route.

    Returns **404** if no route exists at that order.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await MtRoutesController().update_route(order, body))


@router.delete("/flush", response_model=ApiResponse[None], summary="Flush all MT routes")
async def flush_routes():
    """
    Deletes **all** MT routes at once.

    > **Warning:** This is a destructive operation. All routing rules are removed
    > immediately. Any outbound SMS submissions will fail until routes are recreated.

    Use this for a clean rebuild of the routing table.

    Configuration is automatically persisted to disk after flushing.
    """
    await MtRoutesController().flush_routes()
    return empty("All MT routes flushed")


@router.delete("/{order}", response_model=ApiResponse[None], summary="Delete an MT route")
async def delete_route(order: int):
    """
    Deletes a single MT route by its order number.

    **Path parameter:**
    - `order` — route priority number to delete (e.g. `10`)

    Returns **404** if no route exists at that order.

    Configuration is automatically persisted to disk after deletion.
    """
    await MtRoutesController().delete_route(order)
    return empty("MT route deleted")
