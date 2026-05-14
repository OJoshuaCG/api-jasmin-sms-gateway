from fastapi import APIRouter

from app.controllers.http_connectors_controller import HttpConnectorsController
from app.schemas.http_connectors import HttpConnectorCreate, HttpConnectorOut, HttpConnectorUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/http-connectors", tags=["HTTP Connectors"])


@router.get("/", response_model=ApiResponse[list[HttpConnectorOut]], summary="List all HTTP connectors")
async def list_connectors():
    """
    Returns all outbound HTTP connectors.

    HTTP connectors are webhook endpoints where Jasmin delivers MO (mobile-originated)
    messages. When an inbound SMS is received from an SMSC and matched by a MO route,
    Jasmin posts the message payload to the configured URL.

    **Response fields:**
    - `cid` — unique connector ID, referenced in MO routes as `http(<cid>)`
    - `url` — full URL that receives the MO message
    - `method` — HTTP method: `GET` (params in query string) or `POST` (params in form body)

    **MO message payload fields Jasmin sends to the URL:**
    `from`, `to`, `content`, `binary`, `smsc-id`, `priority`, `coding`, `validity-period`, `tags`
    """
    return success(data=await HttpConnectorsController().list_connectors())


@router.get("/{cid}", response_model=ApiResponse[HttpConnectorOut], summary="Get an HTTP connector")
async def get_connector(cid: str):
    """
    Returns a single HTTP connector by its ID.

    **Path parameter:**
    - `cid` — connector identifier (e.g. `webhook_crm`)

    Returns **404** if the connector does not exist.
    """
    return success(data=await HttpConnectorsController().get_connector(cid))


@router.post("/", response_model=ApiResponse[HttpConnectorOut], status_code=201, summary="Create an HTTP connector")
async def create_connector(body: HttpConnectorCreate):
    """
    Creates a new outbound HTTP connector for MO message delivery.

    **Body:**
    ```json
    {
      "cid": "webhook_crm",
      "url": "https://myapp.com/sms/inbound",
      "method": "POST"
    }
    ```

    **Field reference:**

    | Field | Required | Description |
    |---|---|---|
    | `cid` | Yes | Unique connector ID (1–64 chars). Referenced in MO routes as `http(<cid>)` |
    | `url` | Yes | Full URL that receives the MO message (e.g. `https://myapp.com/sms/mo`) |
    | `method` | Yes | `GET` — params in query string · `POST` — params in form body |

    Returns **409** if a connector with the same `cid` already exists.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await HttpConnectorsController().create_connector(body), message="HTTP connector created")


@router.patch("/{cid}", response_model=ApiResponse[HttpConnectorOut], summary="Update an HTTP connector")
async def update_connector(cid: str, body: HttpConnectorUpdate):
    """
    Updates the URL or method of an existing HTTP connector.

    Only the fields included in the body are modified.

    **Example:**
    ```json
    {
      "url": "https://newapp.com/sms/inbound",
      "method": "GET"
    }
    ```

    Returns **404** if the connector does not exist.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await HttpConnectorsController().update_connector(cid, body))


@router.delete("/{cid}", response_model=ApiResponse[None], summary="Delete an HTTP connector")
async def delete_connector(cid: str):
    """
    Deletes an HTTP connector.

    **Path parameter:**
    - `cid` — connector identifier to delete

    Returns **404** if the connector does not exist.

    > **Warning:** Deleting a connector referenced by active MO routes will leave
    > those routes without a valid delivery endpoint. Remove MO route references first.

    Configuration is automatically persisted to disk after deletion.
    """
    await HttpConnectorsController().delete_connector(cid)
    return empty("HTTP connector deleted")
