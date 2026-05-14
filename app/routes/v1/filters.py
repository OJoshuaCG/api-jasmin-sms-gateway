from fastapi import APIRouter

from app.controllers.filters_controller import FiltersController
from app.schemas.filters import FilterCreate, FilterOut, FilterUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/filters", tags=["Filters"])


@router.get("/", response_model=ApiResponse[list[FilterOut]], summary="List all filters")
async def list_filters():
    """
    Returns all Jasmin filters.

    Filters are reusable conditions attached to routes and interceptors to decide
    which messages they handle. Each filter inspects a specific message attribute.

    **Response fields:**
    - `fid` — unique filter identifier
    - `type` — filter type (see types below)
    - `routes` — directions where this filter is used (`MT`, `MO`, or `MT MO`)
    - `description` — compact Jasmin representation (e.g. `<U (uid=myuser)>`)
    - `params` — extracted parameters (key/value pairs from the description)

    **Available filter types and their `params`:**

    | Type | Required param | Example |
    |---|---|---|
    | `TransparentFilter` | _(none)_ | matches all messages |
    | `UserFilter` | `uid` | `{"uid": "user_mx"}` |
    | `ConnectorFilter` | `cid` | `{"cid": "smpp_main"}` |
    | `GroupFilter` | `gid` | `{"gid": "premium"}` |
    | `SourceAddrFilter` | `source_addr` | `{"source_addr": "^254"}` |
    | `DestinationAddrFilter` | `destination_addr` | `{"destination_addr": "^1"}` |
    | `ShortMessageFilter` | `short_message` | `{"short_message": "^STOP"}` |
    | `DateIntervalFilter` | `dateInterval` | `{"dateInterval": "2024-01-01;2024-12-31"}` |
    | `TimeIntervalFilter` | `timeInterval` | `{"timeInterval": "08:00:00;18:00:00"}` |
    | `TagFilter` | `tag` | `{"tag": "99"}` |
    | `EvalPyFilter` | `pyCode` | `{"pyCode": "routable.pdu.params['src'].startswith('254')"}` |

    > **Note:** `params` keys in the list response may use Jasmin's internal abbreviations
    > (`src_addr` instead of `source_addr`, `dst_addr` instead of `destination_addr`).
    > Always use the full names when creating filters.
    """
    return success(data=await FiltersController().list_filters())


@router.get("/{fid}", response_model=ApiResponse[FilterOut], summary="Get a filter")
async def get_filter(fid: str):
    """
    Returns a single filter by its ID.

    **Path parameter:**
    - `fid` — filter identifier (e.g. `ft_pbx`)

    `routes` and `description` will be empty in this response — Jasmin's
    `filter -s` command does not include that information. Use the list endpoint
    for full details.

    Returns **404** if the filter does not exist.
    """
    return success(data=await FiltersController().get_filter(fid))


@router.post("/", response_model=ApiResponse[FilterOut], status_code=201, summary="Create a filter")
async def create_filter(body: FilterCreate):
    """
    Creates a new Jasmin filter.

    **Body examples by type:**

    `UserFilter`:
    ```json
    { "fid": "ft_user_mx", "type": "UserFilter", "params": { "uid": "user_mx" } }
    ```

    `SourceAddrFilter`:
    ```json
    { "fid": "ft_src_ke", "type": "SourceAddrFilter", "params": { "source_addr": "^254" } }
    ```

    `TransparentFilter` (no params):
    ```json
    { "fid": "ft_all", "type": "TransparentFilter", "params": {} }
    ```

    `DateIntervalFilter`:
    ```json
    { "fid": "ft_q1", "type": "DateIntervalFilter", "params": { "dateInterval": "2024-01-01;2024-03-31" } }
    ```

    `TimeIntervalFilter`:
    ```json
    { "fid": "ft_biz", "type": "TimeIntervalFilter", "params": { "timeInterval": "08:00:00;18:00:00" } }
    ```

    `EvalPyFilter`:
    ```json
    { "fid": "ft_ke_src", "type": "EvalPyFilter", "params": { "pyCode": "routable.pdu.params['source_addr'].startswith('254')" } }
    ```

    Returns **409** if a filter with the same `fid` already exists.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await FiltersController().create_filter(body), message="Filter created")


@router.patch("/{fid}", response_model=ApiResponse[FilterOut], summary="Update a filter")
async def update_filter(fid: str, body: FilterUpdate):
    """
    Updates an existing filter.

    > **Important:** Jasmin has no native `filter --update` command.
    > This endpoint **deletes and recreates** the filter internally.
    > The `fid` is preserved.

    **Body:**
    ```json
    { "type": "UserFilter", "params": { "uid": "new_user" } }
    ```

    Both `type` and `params` are required — a filter update always replaces the
    full definition.

    Returns **404** if the filter does not exist.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await FiltersController().update_filter(fid, body))


@router.delete("/{fid}", response_model=ApiResponse[None], summary="Delete a filter")
async def delete_filter(fid: str):
    """
    Deletes a Jasmin filter.

    **Path parameter:**
    - `fid` — filter identifier to delete

    Returns **404** if the filter does not exist.

    > **Warning:** Deleting a filter that is referenced by active routes or interceptors
    > will leave those routes/interceptors without a valid filter. Remove the references
    > before deleting the filter.

    Configuration is automatically persisted to disk after deletion.
    """
    await FiltersController().delete_filter(fid)
    return empty("Filter deleted")
