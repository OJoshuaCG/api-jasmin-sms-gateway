import re

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    uid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique user ID. No spaces allowed. Example: \"user_mx_01\"",
    )
    gid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Group ID this user belongs to. The group must already exist. "
            "Example: \"premium_customers\""
        ),
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Login name for SMPP bind and HTTP API authentication. No spaces allowed. "
            "Example: \"smpp_user1\""
        ),
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Password for SMPP bind and HTTP API authentication.",
    )

    @field_validator("uid", "gid", "username")
    @classmethod
    def no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("must not contain spaces")
        return v

    # Throughput limits (messages/second). None = unlimited.
    mt_throughput: float | None = Field(
        default=None,
        description=(
            "Max MT messages per second this user can submit via HTTP. "
            "None = unlimited. Example: 10.0"
        ),
    )
    mo_throughput: float | None = Field(
        default=None,
        description="Max MO messages per second. None = unlimited.",
    )

    # Balance / SMS quota. None = unlimited (Jasmin uses 'UD').
    balance: float | None = Field(
        default=None,
        description=(
            "Credit balance for prepaid billing. Decremented per message. "
            "None = unlimited. Example: 100.0"
        ),
    )
    sms_count: int | None = Field(
        default=None,
        description=(
            "Max number of MT messages the user can send. "
            "None = unlimited. Example: 500"
        ),
    )

    # MT Messaging authorization flags. None = use Jasmin's default (True).
    mt_auth_priority: bool | None = Field(
        default=None,
        description="Allow user to set message priority. Default: True.",
    )
    mt_auth_validity_period: bool | None = Field(
        default=None,
        description="Allow user to set validity period on messages. Default: True.",
    )
    mt_auth_src_addr: bool | None = Field(
        default=None,
        description="Allow user to set a custom source address (sender ID). Default: True.",
    )
    mt_auth_schedule_at: bool | None = Field(
        default=None,
        description="Allow user to schedule message delivery. Default: True.",
    )
    mt_auth_dlr_level: bool | None = Field(
        default=None,
        description="Allow user to request delivery report level. Default: True.",
    )
    mt_auth_long_content: bool | None = Field(
        default=None,
        description="Allow user to send long (multipart) SMS via HTTP. Default: True.",
    )

    # MT value filters — regex applied to the respective field before routing.
    mt_filter_src_addr: str | None = Field(
        default=None,
        description=(
            "Regex the source address must match, or message is rejected. "
            "Example: \"^254\" (only allow Kenya numbers as source)"
        ),
    )
    mt_filter_dst_addr: str | None = Field(
        default=None,
        description=(
            "Regex the destination address must match. "
            "Example: \"^\\+?[1-9]\\d{6,14}$\""
        ),
    )
    mt_filter_content: str | None = Field(
        default=None,
        description="Regex the message text must match. Example: \"^[A-Za-z0-9 ]+$\"",
    )

    # SMPP server credentials for when this user connects as an SMPP client.
    smpps_allow_bind: bool | None = Field(
        default=None,
        description="Allow this user to bind as an SMPP client. Default: True.",
    )
    smpps_max_bindings: int | None = Field(
        default=None,
        description="Max simultaneous SMPP binds for this user. None = unlimited. Example: 2",
    )
    smpps_quota_sms_count: int | None = Field(
        default=None,
        description="Max messages via SMPP server. None = unlimited.",
    )
    smpps_throughput: float | None = Field(
        default=None,
        description="Max messages/second via SMPP server. None = unlimited.",
    )


class UserUpdate(BaseModel):
    # All fields optional — only provided fields are updated in Jasmin.
    gid: str | None = Field(default=None, description="Move user to a different group.")
    username: str | None = Field(default=None, description="Change login username.")
    password: str | None = Field(default=None, description="Change password.")
    mt_throughput: float | None = Field(default=None, description="Update MT throughput limit.")
    mo_throughput: float | None = Field(default=None, description="Update MO throughput limit.")
    balance: float | None = Field(default=None, description="Update credit balance.")
    sms_count: int | None = Field(default=None, description="Update SMS quota.")
    mt_auth_priority: bool | None = Field(default=None, description="Update priority authorization.")
    mt_auth_validity_period: bool | None = Field(default=None, description="Update validity period authorization.")
    mt_auth_src_addr: bool | None = Field(default=None, description="Update source address override authorization.")
    mt_auth_schedule_at: bool | None = Field(default=None, description="Update schedule authorization.")
    mt_auth_dlr_level: bool | None = Field(default=None, description="Update DLR level authorization.")
    mt_auth_long_content: bool | None = Field(default=None, description="Update long content authorization.")
    mt_filter_src_addr: str | None = Field(default=None, description="Update source address regex filter.")
    mt_filter_dst_addr: str | None = Field(default=None, description="Update destination address regex filter.")
    mt_filter_content: str | None = Field(default=None, description="Update message content regex filter.")
    smpps_allow_bind: bool | None = Field(default=None, description="Update SMPP bind authorization.")
    smpps_max_bindings: int | None = Field(default=None, description="Update max SMPP bindings.")
    smpps_quota_sms_count: int | None = Field(default=None, description="Update SMPP SMS quota.")
    smpps_throughput: float | None = Field(default=None, description="Update SMPP throughput limit.")


class UserStatusUpdate(BaseModel):
    enabled: bool = Field(
        ...,
        description=(
            "Enable (true) or disable (false) the user. "
            "A disabled user cannot send messages or bind via SMPP."
        ),
    )


class UserOut(BaseModel):
    uid: str
    gid: str
    username: str = ""
    enabled: bool
    mt_throughput: float | None = None
    mo_throughput: float | None = None
    balance: float | None = None
    sms_count: int | None = None
    mt_auth_priority: bool = True
    mt_auth_validity_period: bool = True
    mt_auth_src_addr: bool = True
    mt_auth_schedule_at: bool = True
    mt_auth_dlr_level: bool = True
    mt_auth_long_content: bool = True
    mt_filter_src_addr: str | None = None
    mt_filter_dst_addr: str | None = None
    mt_filter_content: str | None = None
    smpps_allow_bind: bool = True
    smpps_max_bindings: int | None = None
    smpps_quota_sms_count: int | None = None
    smpps_throughput: float | None = None
