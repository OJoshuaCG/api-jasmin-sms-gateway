from fastapi import APIRouter

from app.controllers.smpp_connectors_controller import SmppConnectorsController
from app.schemas.smpp_connectors import (
    SmppConnectorCreate,
    SmppConnectorOut,
    SmppConnectorStatusOut,
    SmppConnectorUpdate,
)
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/smpp-connectors", tags=["SMPP Connectors"])


@router.get("/", response_model=ApiResponse[list[SmppConnectorOut]], summary="List all SMPP connectors")
async def list_connectors():
    """
    Returns all outbound SMPP connectors.

    SMPP connectors represent outbound connections from Jasmin to an SMSC
    (carrier or aggregator). Jasmin uses them to deliver MT (mobile-terminated)
    messages to the network. After creating a connector, start it to open the
    SMPP session.

    **Key response fields:**
    - `cid` — unique connector ID, referenced in MT routes as `smppc(<cid>)`
    - `host` / `port` — SMSC address
    - `username` — SMPP `system_id` for authentication
    - `bind_to` — bind type: `transceiver`, `transmitter`, or `receiver`
    - `submit_throughput` — max submit_sm/sec; `null` = unlimited
    - `reconnect_on_connection_loss` — auto-reconnect on session drop (default: `true`)
    - `reconnect_on_connection_failure` — auto-retry on initial connect failure (default: `true`)
    """
    return success(data=await SmppConnectorsController().list_connectors())


@router.get("/{cid}", response_model=ApiResponse[SmppConnectorOut], summary="Get an SMPP connector")
async def get_connector(cid: str):
    """
    Returns a single SMPP connector by its ID.

    **Path parameter:**
    - `cid` — connector identifier (e.g. `carrier_mx`)

    Returns **404** if the connector does not exist.
    """
    return success(data=await SmppConnectorsController().get_connector(cid))


@router.post("/", response_model=ApiResponse[SmppConnectorOut], status_code=201, summary="Create an SMPP connector")
async def create_connector(body: SmppConnectorCreate):
    """
    Creates a new outbound SMPP connector.

    The connector is created in **stopped** state. Call `POST /{cid}/start`
    to open the SMPP session after creation.

    **Minimal body:**
    ```json
    {
      "cid": "carrier_mx",
      "host": "smpp.carrier.com",
      "port": 2775,
      "username": "jasmin_mx",
      "password": "s3cr3t"
    }
    ```

    **Full body with optional fields:**
    ```json
    {
      "cid": "carrier_mx",
      "host": "smpp.carrier.com",
      "port": 2775,
      "username": "jasmin_mx",
      "password": "s3cr3t",
      "bind_to": "transceiver",
      "system_type": "",
      "source_addr_ton": 1,
      "source_addr_npi": 1,
      "dest_addr_ton": 1,
      "dest_addr_npi": 1,
      "submit_throughput": 50.0,
      "dlr_expiry": 86400,
      "reconnect_on_connection_loss": true,
      "reconnect_on_connection_loss_delay": 10,
      "reconnect_on_connection_failure": true,
      "reconnect_on_connection_failure_delay": 10
    }
    ```

    **Field reference:**

    | Field | Default | Description |
    |---|---|---|
    | `bind_to` | `transceiver` | `transceiver` (send+receive), `transmitter` (send only), `receiver` (receive only) |
    | `source_addr_ton` | Jasmin default | TON: `0`=Unknown, `1`=International, `5`=Alphanumeric |
    | `source_addr_npi` | Jasmin default | NPI: `0`=Unknown, `1`=ISDN/E.164 |
    | `dest_addr_ton` | Jasmin default | TON for destination address |
    | `dest_addr_npi` | Jasmin default | NPI for destination address |
    | `submit_throughput` | unlimited | Max submit_sm/sec sent to the SMSC |
    | `dlr_expiry` | Jasmin default | Seconds to wait for a DLR before expiring |
    | `reconnect_on_connection_loss` | `true` | Auto-reconnect on session drop |
    | `reconnect_on_connection_loss_delay` | `10` | Seconds before reconnect attempt |
    | `reconnect_on_connection_failure` | `true` | Auto-retry on initial connect failure |
    | `reconnect_on_connection_failure_delay` | `10` | Seconds before retry |

    Returns **409** if a connector with the same `cid` already exists.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await SmppConnectorsController().create_connector(body), message="Connector created")


@router.patch("/{cid}", response_model=ApiResponse[SmppConnectorOut], summary="Update an SMPP connector")
async def update_connector(cid: str, body: SmppConnectorUpdate):
    """
    Updates one or more fields of an existing SMPP connector.

    Only the fields included in the body are modified.

    > **Important:** The connector must be **stopped** before updating.
    > Jasmin does not apply changes to a running connector session.
    > Call `POST /{cid}/stop` first, then update, then `POST /{cid}/start`.

    **Example — update host and throughput:**
    ```json
    {
      "host": "smpp2.carrier.com",
      "submit_throughput": 100.0
    }
    ```

    Returns **404** if the connector does not exist.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await SmppConnectorsController().update_connector(cid, body))


@router.delete("/{cid}", response_model=ApiResponse[None], summary="Delete an SMPP connector")
async def delete_connector(cid: str):
    """
    Deletes an SMPP connector.

    **Path parameter:**
    - `cid` — connector identifier to delete

    > **Warning:** The connector should be stopped before deleting.
    > Deleting a connector referenced by active MT routes will leave those routes
    > without a valid connector.

    Returns **404** if the connector does not exist.

    Configuration is automatically persisted to disk after deletion.
    """
    await SmppConnectorsController().delete_connector(cid)
    return empty("Connector deleted")


@router.post("/{cid}/start", response_model=ApiResponse[SmppConnectorStatusOut], summary="Start an SMPP connector")
async def start_connector(cid: str):
    """
    Starts an SMPP connector and opens the session to the SMSC.

    Jasmin will attempt to bind to the carrier using the configured credentials.
    Use `GET /{cid}/status` to check the connection state after starting.

    **Status values after start:**
    - `started` — connector is running but not yet bound
    - `connecting` — attempting the TCP connection
    - `bound_TRX` / `bound_TX` / `bound_RX` — successfully bound

    Returns **404** if the connector does not exist.
    """
    return success(data=await SmppConnectorsController().start_connector(cid), message="Connector started")


@router.post("/{cid}/stop", response_model=ApiResponse[SmppConnectorStatusOut], summary="Stop an SMPP connector")
async def stop_connector(cid: str):
    """
    Stops an SMPP connector and closes the session to the SMSC.

    Jasmin will send an `unbind` PDU and close the TCP connection.
    In-flight messages may be lost. Stop the connector only when no
    traffic is being processed.

    Returns **404** if the connector does not exist.
    """
    return success(data=await SmppConnectorsController().stop_connector(cid), message="Connector stopped")


@router.get("/{cid}/status", response_model=ApiResponse[SmppConnectorStatusOut], summary="Get connector status")
async def get_connector_status(cid: str):
    """
    Returns the current operational status of an SMPP connector.

    **Response fields:**
    - `cid` — connector identifier
    - `status` — current state: `stopped`, `started`, `connecting`, `bound_TRX`, `bound_TX`, `bound_RX`
    - `sessions_count` — number of active SMPP sessions (usually 0 or 1)
    - `last_error` — last error message from the connector, if any

    Returns **404** if the connector does not exist.
    """
    return success(data=await SmppConnectorsController().get_connector_status(cid))
