from fastapi import APIRouter

from app.controllers.stats_controller import StatsController
from app.schemas.stats import (
    GlobalStatsOut,
    HttpApiStatsOut,
    SmppConnectorStatsOut,
    SmppServerApiStatsOut,
    UserStatsOut,
)
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/", response_model=ApiResponse[GlobalStatsOut], summary="Get global stats overview")
async def get_global_stats():
    """
    Returns a consolidated stats overview for all Jasmin resources.

    Makes 4 parallel calls to jcli (`stats --smppcs`, `stats --users`,
    `stats --httpapi`, `stats --smppsapi`) and aggregates the results.

    > **Note:** Stats reset to zero every time Jasmin restarts.

    **Response structure:**
    ```json
    {
      "data": {
        "smpp_connectors": [
          {
            "cid": "carrier_mx",
            "connected_at": "2024-01-15 08:30:00",
            "bound_at": "2024-01-15 08:30:01",
            "submits": "1500/1498",
            "delivers": "0/0",
            "qos_errors": 0,
            "other_errors": 2
          }
        ],
        "users": [
          {
            "uid": "user_mx_01",
            "smpp_bound_connections": 1,
            "smpp_last_activity": "2024-01-15 12:00:00",
            "http_request_count": 450,
            "http_last_activity": "2024-01-15 12:05:00"
          }
        ],
        "http_api": { "request_count": 1200, "success_count": 1195, ... },
        "smpp_server_api": { "connected_count": 3, "submit_sm_count": 800, ... }
      }
    }
    ```

    **`submits` format:** `"requested/accepted"` (e.g. `"1500/1498"` means 1500 submitted, 1498 accepted)
    """
    return success(data=await StatsController().get_global_stats())


@router.get("/smpp-connectors/{cid}", response_model=ApiResponse[SmppConnectorStatsOut], summary="Get SMPP connector stats")
async def get_smpp_connector_stats(cid: str):
    """
    Returns detailed real-time stats for a specific SMPP connector.

    **Path parameter:**
    - `cid` — connector identifier (e.g. `carrier_mx`)

    **Response fields:**

    | Field | Description |
    |---|---|
    | `created_at` | Timestamp when the connector was initialized |
    | `connected_at` | Last successful TCP connection timestamp |
    | `bound_at` | Last successful SMPP bind timestamp |
    | `disconnected_at` | Last disconnection timestamp |
    | `last_received_pdu_at` | Timestamp of the last received PDU |
    | `last_sent_pdu_at` | Timestamp of the last sent PDU |
    | `connected_count` | Total number of TCP connections established |
    | `bound_count` | Total number of successful SMPP binds |
    | `disconnected_count` | Total number of disconnections |
    | `submit_sm_request_count` | Total submit_sm PDUs sent to the SMSC |
    | `submit_sm_count` | Total submit_sm_resp with success status received |
    | `deliver_sm_count` | Total deliver_sm PDUs received (MO messages) |
    | `elink_count` | Total enquire_link PDUs exchanged |
    | `throttling_error_count` | Total submit_sm rejected with throttling error |
    | `other_submit_error_count` | Total submit_sm rejected with other errors |
    | `interceptor_error_count` | Total messages rejected by interceptors |
    | `interceptor_count` | Total messages processed by interceptors |

    All `null` timestamps indicate the event has never occurred since last restart.

    Returns **404** if the connector does not exist.
    """
    return success(data=await StatsController().get_smppccm_stats(cid))


@router.get("/users/{uid}", response_model=ApiResponse[UserStatsOut], summary="Get user stats")
async def get_user_stats(uid: str):
    """
    Returns detailed real-time stats for a specific Jasmin user.

    Stats are split by protocol: **SMPP server** (inbound binds from the user)
    and **HTTP API** (outbound send requests from the user).

    **Path parameter:**
    - `uid` — user identifier (e.g. `user_mx_01`)

    **Response fields:**

    *SMPP Server stats:*
    - `smpp_bind_count` — total SMPP bind attempts from this user
    - `smpp_unbind_count` — total SMPP unbind events
    - `smpp_bound_connections` — current active SMPP binds (live counter)
    - `smpp_submit_sm_request_count` — total submit_sm sent via SMPP
    - `smpp_submit_sm_count` — successfully accepted submit_sm via SMPP
    - `smpp_deliver_sm_count` — total deliver_sm sent to this user via SMPP
    - `smpp_throttling_error_count` — throttling rejections via SMPP
    - `smpp_last_activity_at` — last SMPP activity timestamp

    *HTTP API stats:*
    - `http_connects_count` — total HTTP send requests
    - `http_submit_sm_request_count` — total submit_sm generated via HTTP
    - `http_balance_request_count` — total balance check requests
    - `http_rate_request_count` — total rate check requests
    - `http_last_activity_at` — last HTTP activity timestamp

    Returns **404** if the user does not exist.
    """
    return success(data=await StatsController().get_user_stats(uid))


@router.get("/http-api", response_model=ApiResponse[HttpApiStatsOut], summary="Get HTTP API stats")
async def get_httpapi_stats():
    """
    Returns aggregated stats for Jasmin's HTTP send API (all users combined).

    **Response fields:**

    | Field | Description |
    |---|---|
    | `created_at` | Timestamp when the HTTP API service started |
    | `last_request_at` | Timestamp of the last request received |
    | `last_success_at` | Timestamp of the last successfully submitted message |
    | `request_count` | Total HTTP requests received |
    | `success_count` | Total messages successfully submitted to SMSC |
    | `auth_error_count` | Requests rejected for bad credentials |
    | `route_error_count` | Requests rejected because no MT route matched |
    | `interceptor_error_count` | Messages rejected by an interceptor script |
    | `interceptor_count` | Total messages processed by interceptors |
    | `throughput_error_count` | Requests throttled due to rate limiting |
    | `charging_error_count` | Requests rejected due to insufficient balance |
    | `server_error_count` | Internal server errors |
    """
    return success(data=await StatsController().get_httpapi_stats())


@router.get("/smpp-server-api", response_model=ApiResponse[SmppServerApiStatsOut], summary="Get SMPP server API stats")
async def get_smppsapi_stats():
    """
    Returns aggregated stats for Jasmin's inbound SMPP server (all bound users combined).

    This reflects the activity of the SMPP server that external clients
    (ESME / SMPP clients) connect to.

    **Response fields:**

    | Field | Description |
    |---|---|
    | `created_at` | Timestamp when the SMPP server started |
    | `last_received_pdu_at` | Last PDU received from any client |
    | `last_sent_pdu_at` | Last PDU sent to any client |
    | `connected_count` | Current active TCP connections |
    | `connect_count` | Total TCP connections ever established |
    | `disconnect_count` | Total disconnections |
    | `bound_trx_count` | Current transceiver binds |
    | `bound_rx_count` | Current receiver binds |
    | `bound_tx_count` | Current transmitter binds |
    | `bind_trx_count` | Total transceiver bind attempts |
    | `bind_rx_count` | Total receiver bind attempts |
    | `bind_tx_count` | Total transmitter bind attempts |
    | `unbind_count` | Total unbind events |
    | `submit_sm_request_count` | Total submit_sm PDUs received from clients |
    | `submit_sm_count` | Successfully forwarded submit_sm |
    | `deliver_sm_count` | Total deliver_sm PDUs sent to clients |
    | `elink_count` | Total enquire_link PDUs |
    | `throttling_error_count` | Throttling rejections |
    | `other_submit_error_count` | Other submit errors |
    | `interceptor_error_count` | Messages rejected by interceptors |
    | `interceptor_count` | Total messages processed by interceptors |
    """
    return success(data=await StatsController().get_smppsapi_stats())
