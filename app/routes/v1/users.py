from fastapi import APIRouter

from app.controllers.users_controller import UsersController
from app.schemas.users import UserCreate, UserOut, UserStatusUpdate, UserUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=ApiResponse[list[UserOut]], summary="List all users")
async def list_users():
    """
    Returns all Jasmin users.

    Users authenticate for SMS submission via HTTP API or SMPP bind.
    Each user belongs to exactly one group and has configurable quota,
    throughput, authorization flags, and value filters.

    **Key response fields:**
    - `uid` — unique user identifier
    - `gid` — group this user belongs to
    - `username` — login name for SMPP and HTTP API
    - `enabled` — whether the user can send messages
    - `balance` / `sms_count` — prepaid credit; `null` = unlimited
    - `mt_throughput` / `smpps_throughput` — messages/second limits; `null` = unlimited
    - `mt_auth_*` — authorization flags (priority, src address override, etc.)
    - `mt_filter_*` — regex filters applied before routing
    - `smpps_*` — SMPP server (inbound bind) settings
    """
    return success(data=await UsersController().list_users())


@router.get("/{uid}", response_model=ApiResponse[UserOut], summary="Get a user")
async def get_user(uid: str):
    """
    Returns a single user by UID.

    **Path parameter:**
    - `uid` — user identifier (e.g. `user_mx_01`)

    Returns **404** if the user does not exist.
    """
    return success(data=await UsersController().get_user(uid))


@router.post("/", response_model=ApiResponse[UserOut], status_code=201, summary="Create a user")
async def create_user(body: UserCreate):
    """
    Creates a new Jasmin user.

    **Minimal body (required fields only):**
    ```json
    {
      "uid": "user_mx_01",
      "gid": "premium_customers",
      "username": "smpp_mx01",
      "password": "s3cr3t"
    }
    ```

    **Full body with optional fields:**
    ```json
    {
      "uid": "user_mx_01",
      "gid": "premium_customers",
      "username": "smpp_mx01",
      "password": "s3cr3t",
      "balance": 100.0,
      "sms_count": 500,
      "mt_throughput": 10.0,
      "smpps_throughput": 5.0,
      "mt_auth_src_addr": true,
      "mt_auth_long_content": true,
      "mt_filter_src_addr": "^254",
      "mt_filter_dst_addr": null,
      "smpps_allow_bind": true,
      "smpps_max_bindings": 2
    }
    ```

    **Field reference:**

    | Field | Default | Description |
    |---|---|---|
    | `balance` | unlimited | Prepaid credit balance (decremented per message) |
    | `sms_count` | unlimited | Max total MT messages allowed |
    | `mt_quota_early_percent` | unlimited | Early quota warning threshold (%) |
    | `mt_throughput` | unlimited | Max MT msg/sec via HTTP API |
    | `smpps_throughput` | unlimited | Max MT msg/sec via SMPP server |
    | `mt_auth_http_send` | `true` | Allow sending via HTTP API |
    | `mt_auth_http_balance` | `true` | Allow balance check via HTTP |
    | `mt_auth_http_rate` | `true` | Allow rate check via HTTP |
    | `mt_auth_http_bulk` | `false` | Allow bulk send via HTTP |
    | `mt_auth_smpps_send` | `true` | Allow sending via SMPP server |
    | `mt_auth_priority` | `true` | Allow setting message priority |
    | `mt_auth_validity_period` | `true` | Allow setting validity period |
    | `mt_auth_src_addr` | `true` | Allow custom sender ID |
    | `mt_auth_schedule_at` | `true` | Allow scheduled delivery |
    | `mt_auth_dlr_level` | `true` | Allow DLR level selection |
    | `mt_auth_http_dlr_method` | `true` | Allow DLR callback method selection |
    | `mt_auth_long_content` | `true` | Allow long (multipart) SMS via HTTP |
    | `mt_auth_hex_content` | `true` | Allow hex-encoded message content |
    | `mt_filter_src_addr` | `null` | Regex source address must match |
    | `mt_filter_dst_addr` | `null` | Regex destination must match |
    | `mt_filter_content` | `null` | Regex message text must match |
    | `mt_filter_priority` | `null` | Regex priority value must match |
    | `mt_filter_validity_period` | `null` | Regex validity period must match |
    | `mt_default_src_addr` | `null` | Default source address when none provided |
    | `smpps_allow_bind` | `true` | Allow SMPP inbound bind |
    | `smpps_max_bindings` | unlimited | Max simultaneous SMPP binds |

    Returns **404** if the referenced `gid` does not exist.
    Returns **409** if a user with the same `uid` already exists.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await UsersController().create_user(body), message="User created")


@router.patch("/{uid}", response_model=ApiResponse[UserOut], summary="Update a user")
async def update_user(uid: str, body: UserUpdate):
    """
    Updates one or more fields of an existing user.

    Only the fields included in the body are modified. Omitted fields retain
    their current values in Jasmin.

    **Example — change group and throughput:**
    ```json
    {
      "gid": "new_group",
      "mt_throughput": 20.0
    }
    ```

    **Example — remove balance limit (set to unlimited):**
    ```json
    { "balance": null }
    ```

    Returns **404** if the user does not exist.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await UsersController().update_user(uid, body))


@router.delete("/{uid}", response_model=ApiResponse[None], summary="Delete a user")
async def delete_user(uid: str):
    """
    Deletes a Jasmin user.

    **Path parameter:**
    - `uid` — user identifier to delete

    Returns **404** if the user does not exist.

    Configuration is automatically persisted to disk after deletion.
    """
    await UsersController().delete_user(uid)
    return empty("User deleted")


@router.patch("/{uid}/status", response_model=ApiResponse[UserOut], summary="Enable or disable a user")
async def update_user_status(uid: str, body: UserStatusUpdate):
    """
    Enables or disables a specific user without modifying any other settings.

    **Body:**
    ```json
    { "enabled": false }
    ```

    A disabled user:
    - Cannot submit MT messages via HTTP API
    - Cannot bind via SMPP
    - Returns an authentication error on any attempt

    Returns **404** if the user does not exist.

    Configuration is automatically persisted to disk after the update.
    """
    return success(data=await UsersController().update_user_status(uid, body))
