from fastapi import APIRouter, Query

from app.controllers.sms_controller import SmsController
from app.schemas.sms import SmsBinaryRequest, SmsBalanceOut, SmsRateOut, SmsSendOut, SmsSendRequest
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/sms", tags=["SMS"])


@router.post("/send", response_model=ApiResponse[SmsSendOut], summary="Send an SMS")
async def send_sms(body: SmsSendRequest):
    """
    Sends an outbound SMS through Jasmin's HTTP API.

    Jasmin authenticates the user, evaluates MT interceptors, selects an MT route,
    and delivers the message via the matching SMPP connector. Optionally requests
    a delivery receipt (DLR) posted to `dlr_url`.

    **Body:**
    ```json
    {
      "username": "user_mx_01",
      "password": "s3cr3t",
      "to": "+525512345678",
      "content": "Hello from Jasmin!",
      "from": "MyBrand",
      "coding": 0,
      "dlr": "yes",
      "dlr_url": "https://myapp.com/dlr",
      "dlr_level": 3,
      "dlr_method": "POST",
      "priority": 0,
      "tags": []
    }
    ```

    **Field reference:**

    | Field | Required | Default | Description |
    |---|---|---|---|
    | `username` | Yes | — | Jasmin user ID for authentication |
    | `password` | Yes | — | Jasmin user password |
    | `to` | Yes | — | Destination MSISDN (E.164 recommended, e.g. `+525512345678`) |
    | `content` | Yes | — | Message text |
    | `from` (alias) | No | — | Sender ID or source MSISDN |
    | `coding` | No | `0` | Data coding scheme: `0`=GSM7, `1`=Binary, `8`=UCS2 |
    | `dlr` | No | `"no"` | Request delivery receipt: `"yes"` or `"no"` |
    | `dlr_url` | No | — | URL to receive the DLR callback (required if `dlr="yes"`) |
    | `dlr_level` | No | — | DLR level: `1`=final, `2`=intermediate, `3`=both |
    | `dlr_method` | No | — | HTTP method for DLR callback: `GET` or `POST` |
    | `priority` | No | — | Message priority: `0`–`3` (requires user `mt_auth_priority`) |
    | `schedule_delivery_time` | No | — | Scheduled delivery (format: `YYMMDDHHmmss000R`) |
    | `validity_period` | No | — | Validity period (format: `YYMMDDHHmmss000R`) |
    | `tags` | No | `[]` | Numeric tags to attach to the message |

    **Response:**
    ```json
    { "data": { "message_id": "40d2a7f3-..." } }
    ```

    Returns **400** if the user has insufficient balance, the route is not found,
    or the message is rejected by an interceptor.
    Returns **401** if credentials are invalid.
    """
    return success(data=await SmsController().send(body))


@router.post("/send/binary", response_model=ApiResponse[SmsSendOut], summary="Send a binary SMS")
async def send_binary_sms(body: SmsBinaryRequest):
    """
    Sends a binary SMS using hex-encoded content.

    Used for WAP push, ringtones, vCards, or any non-text payload that requires
    raw binary delivery via the SMPP `data_coding=1` scheme.

    **Body:**
    ```json
    {
      "username": "user_mx_01",
      "password": "s3cr3t",
      "to": "+525512345678",
      "hex_content": "48656c6c6f",
      "coding": 1,
      "from": "MyBrand",
      "dlr": "no"
    }
    ```

    **Field reference:**

    | Field | Required | Default | Description |
    |---|---|---|---|
    | `username` | Yes | — | Jasmin user ID |
    | `password` | Yes | — | Jasmin user password |
    | `to` | Yes | — | Destination MSISDN |
    | `hex_content` | Yes | — | Message payload as hex string (e.g. `48656c6c6f` = "Hello") |
    | `coding` | No | `1` | Data coding: `1`=Binary, `4`=8-bit, `8`=UCS2 |
    | `from` (alias) | No | — | Sender ID |
    | `dlr` | No | `"no"` | Request DLR: `"yes"` or `"no"` |
    | `dlr_url` | No | — | DLR callback URL |
    | `dlr_level` | No | — | DLR level: `1`, `2`, or `3` |
    | `dlr_method` | No | — | DLR HTTP method: `GET` or `POST` |

    **Response:**
    ```json
    { "data": { "message_id": "40d2a7f3-..." } }
    ```
    """
    return success(data=await SmsController().send_binary(body))


@router.get("/rate", response_model=ApiResponse[SmsRateOut], summary="Get message rate for a user")
async def get_rate(
    username: str = Query(..., description="Jasmin username", example="user_mx_01"),
    password: str = Query(..., description="Jasmin password", example="s3cr3t"),
    to: str = Query(..., description="Destination MSISDN", example="+525512345678"),
    sender: str | None = Query(default=None, alias="from", description="Sender ID or source address", example="MyBrand"),
    content: str | None = Query(default=None, description="Message content used to evaluate the rate", example="Hello"),
):
    """
    Returns the per-message rate that Jasmin would charge the user for a given destination.

    Jasmin evaluates the MT routing table to determine which connector (and therefore
    which rate) would be applied. Useful for rate previews before submission.

    **Query parameters:**
    - `username` — Jasmin user ID
    - `password` — Jasmin user password
    - `to` — destination MSISDN (e.g. `+525512345678`)
    - `from` — sender ID (optional)
    - `content` — message text (optional, used for content-based filters)

    **Response:**
    ```json
    {
      "data": {
        "rate": 0.05,
        "unit": "per_message",
        "connector_id": "carrier_mx"
      }
    }
    ```

    Returns **412** if the user has no valid route for the given destination.
    Returns **401** if credentials are invalid.
    """
    return success(data=await SmsController().rate(username, password, to, sender, content))


@router.get("/balance", response_model=ApiResponse[SmsBalanceOut], summary="Get user balance")
async def get_balance(
    username: str = Query(..., description="Jasmin username", example="user_mx_01"),
    password: str = Query(..., description="Jasmin password", example="s3cr3t"),
):
    """
    Returns the current credit balance and SMS quota for a Jasmin user.

    **Query parameters:**
    - `username` — Jasmin user ID
    - `password` — Jasmin user password

    **Response:**
    ```json
    {
      "data": {
        "balance": 87.50,
        "sms_count": null
      }
    }
    ```

    **Response fields:**
    - `balance` — remaining credit balance (`null` = unlimited)
    - `sms_count` — remaining SMS count (`null` = unlimited or not applicable)

    Returns **401** if credentials are invalid.
    """
    return success(data=await SmsController().balance(username, password))
