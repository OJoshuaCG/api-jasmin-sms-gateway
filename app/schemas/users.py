from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_identifier, validate_no_control_chars


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

    @field_validator("uid", "gid")
    @classmethod
    def validate_identifiers(cls, v: str) -> str:
        return validate_identifier(v, "field")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if ' ' in v:
            raise ValueError("must not contain spaces")
        return validate_no_control_chars(v, "username")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_no_control_chars(v, "password")

    @field_validator("mt_filter_src_addr", "mt_filter_dst_addr", "mt_filter_content")
    @classmethod
    def validate_mt_filters(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, "filter")
        return v

    # MT Quota — jcli: mt_messaging_cred quota *
    mt_throughput: float | None = Field(
        default=None,
        description="Max MT messages/second via HTTP (mt_messaging_cred quota http_throughput). None = unlimited.",
    )
    smpps_throughput: float | None = Field(
        default=None,
        description="Max MT messages/second via SMPP server (mt_messaging_cred quota smpps_throughput). None = unlimited.",
    )
    balance: float | None = Field(
        default=None,
        description="Credit balance for prepaid billing. Decremented per message. None = unlimited.",
    )
    sms_count: int | None = Field(
        default=None,
        description="Max number of MT messages the user can send. None = unlimited.",
    )
    mt_quota_early_percent: float | None = Field(
        default=None,
        description="Percentage of quota remaining that triggers early warning. None = unlimited.",
    )

    # MT Auth — jcli: mt_messaging_cred authorization *
    mt_auth_http_send: bool | None = Field(default=None, description="Allow sending MT via HTTP API. Default: True.")
    mt_auth_http_balance: bool | None = Field(default=None, description="Allow checking balance via HTTP API. Default: True.")
    mt_auth_http_rate: bool | None = Field(default=None, description="Allow checking rate via HTTP API. Default: True.")
    mt_auth_http_bulk: bool | None = Field(default=None, description="Allow bulk sending via HTTP API. Default: False.")
    mt_auth_smpps_send: bool | None = Field(default=None, description="Allow sending MT via SMPP server. Default: True.")
    mt_auth_long_content: bool | None = Field(default=None, description="Allow long (multipart) SMS via HTTP. Default: True.")
    mt_auth_dlr_level: bool | None = Field(default=None, description="Allow requesting DLR level. Default: True.")
    mt_auth_http_dlr_method: bool | None = Field(default=None, description="Allow specifying DLR callback HTTP method. Default: True.")
    mt_auth_src_addr: bool | None = Field(default=None, description="Allow setting a custom source address. Default: True.")
    mt_auth_priority: bool | None = Field(default=None, description="Allow setting message priority. Default: True.")
    mt_auth_validity_period: bool | None = Field(default=None, description="Allow setting validity period. Default: True.")
    mt_auth_schedule_at: bool | None = Field(default=None, description="Allow scheduling message delivery. Default: True.")
    mt_auth_hex_content: bool | None = Field(default=None, description="Allow sending hex-encoded content. Default: True.")

    # MT Value Filters — jcli: mt_messaging_cred valuefilter *
    mt_filter_src_addr: str | None = Field(
        default=None,
        description="Regex the source address must match. Example: \"^254\"",
    )
    mt_filter_dst_addr: str | None = Field(
        default=None,
        description="Regex the destination address must match. Example: \"^\\+?[1-9]\\d{6,14}$\"",
    )
    mt_filter_content: str | None = Field(
        default=None,
        description="Regex the message text must match. Example: \"^[A-Za-z0-9 ]+$\"",
    )
    mt_filter_priority: str | None = Field(
        default=None,
        description="Regex the priority value must match. Default: \"^[0-3]$\"",
    )
    mt_filter_validity_period: str | None = Field(
        default=None,
        description="Regex the validity period must match. Default: \"^\\d+$\"",
    )

    # MT Default Values — jcli: mt_messaging_cred defaultvalue *
    mt_default_src_addr: str | None = Field(
        default=None,
        description="Default source address applied when user does not provide one. None = no default.",
    )

    # SMPP Server credentials — jcli: smpps_cred *
    smpps_allow_bind: bool | None = Field(default=None, description="Allow this user to bind as an SMPP client. Default: True.")
    smpps_max_bindings: int | None = Field(default=None, description="Max simultaneous SMPP binds. None = unlimited.")


class UserUpdate(BaseModel):
    # All fields optional — only provided fields are updated in Jasmin.
    gid: str | None = Field(default=None, description="Move user to a different group.")
    username: str | None = Field(default=None, description="Change login username.")
    password: str | None = Field(default=None, description="Change password.")

    @field_validator("gid")
    @classmethod
    def validate_gid(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_identifier(v, "gid")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is not None:
            if ' ' in v:
                raise ValueError("must not contain spaces")
            return validate_no_control_chars(v, "username")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, "password")
        return v

    @field_validator("mt_filter_src_addr", "mt_filter_dst_addr", "mt_filter_content",
                     "mt_filter_priority", "mt_filter_validity_period")
    @classmethod
    def validate_mt_filters(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, "filter")
        return v

    # MT Quota
    mt_throughput: float | None = Field(default=None, description="Update HTTP MT throughput limit (msg/s).")
    smpps_throughput: float | None = Field(default=None, description="Update SMPP MT throughput limit (msg/s).")
    balance: float | None = Field(default=None, description="Update credit balance.")
    sms_count: int | None = Field(default=None, description="Update SMS quota.")
    mt_quota_early_percent: float | None = Field(default=None, description="Update early quota warning percentage.")

    # MT Auth
    mt_auth_http_send: bool | None = Field(default=None, description="Update HTTP send authorization.")
    mt_auth_http_balance: bool | None = Field(default=None, description="Update HTTP balance check authorization.")
    mt_auth_http_rate: bool | None = Field(default=None, description="Update HTTP rate check authorization.")
    mt_auth_http_bulk: bool | None = Field(default=None, description="Update HTTP bulk send authorization.")
    mt_auth_smpps_send: bool | None = Field(default=None, description="Update SMPP send authorization.")
    mt_auth_long_content: bool | None = Field(default=None, description="Update long content authorization.")
    mt_auth_dlr_level: bool | None = Field(default=None, description="Update DLR level authorization.")
    mt_auth_http_dlr_method: bool | None = Field(default=None, description="Update HTTP DLR method authorization.")
    mt_auth_src_addr: bool | None = Field(default=None, description="Update source address override authorization.")
    mt_auth_priority: bool | None = Field(default=None, description="Update priority authorization.")
    mt_auth_validity_period: bool | None = Field(default=None, description="Update validity period authorization.")
    mt_auth_schedule_at: bool | None = Field(default=None, description="Update schedule delivery authorization.")
    mt_auth_hex_content: bool | None = Field(default=None, description="Update hex content authorization.")

    # MT Value Filters
    mt_filter_src_addr: str | None = Field(default=None, description="Update source address regex filter.")
    mt_filter_dst_addr: str | None = Field(default=None, description="Update destination address regex filter.")
    mt_filter_content: str | None = Field(default=None, description="Update message content regex filter.")
    mt_filter_priority: str | None = Field(default=None, description="Update priority regex filter.")
    mt_filter_validity_period: str | None = Field(default=None, description="Update validity period regex filter.")

    # MT Default Values
    mt_default_src_addr: str | None = Field(default=None, description="Update default source address.")

    # SMPP Server creds
    smpps_allow_bind: bool | None = Field(default=None, description="Update SMPP bind authorization.")
    smpps_max_bindings: int | None = Field(default=None, description="Update max SMPP bindings.")


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

    # MT Quota
    mt_throughput: float | None = None
    smpps_throughput: float | None = None
    balance: float | None = None
    sms_count: int | None = None
    mt_quota_early_percent: float | None = None

    # MT Auth
    mt_auth_http_send: bool = True
    mt_auth_http_balance: bool = True
    mt_auth_http_rate: bool = True
    mt_auth_http_bulk: bool = False
    mt_auth_smpps_send: bool = True
    mt_auth_long_content: bool = True
    mt_auth_dlr_level: bool = True
    mt_auth_http_dlr_method: bool = True
    mt_auth_src_addr: bool = True
    mt_auth_priority: bool = True
    mt_auth_validity_period: bool = True
    mt_auth_schedule_at: bool = True
    mt_auth_hex_content: bool = True

    # MT Value Filters
    mt_filter_src_addr: str | None = None
    mt_filter_dst_addr: str | None = None
    mt_filter_content: str | None = None
    mt_filter_priority: str | None = None
    mt_filter_validity_period: str | None = None

    # MT Default Values
    mt_default_src_addr: str | None = None

    # SMPP Server creds
    smpps_allow_bind: bool = True
    smpps_max_bindings: int | None = None
