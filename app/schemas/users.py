from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    uid: str = Field(..., min_length=1, max_length=64)
    gid: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)
    # Throughput
    mt_throughput: float | None = None
    mo_throughput: float | None = None
    # Balance / SMS quota
    balance: float | None = None
    sms_count: int | None = None
    # MT Messaging — Authorization (None = omit, Jasmin uses its own default of True)
    mt_auth_priority: bool | None = None
    mt_auth_validity_period: bool | None = None
    mt_auth_src_addr: bool | None = None
    mt_auth_schedule_at: bool | None = None
    mt_auth_dlr_level: bool | None = None
    mt_auth_long_content: bool | None = None
    # MT Messaging — Value Filters
    mt_filter_src_addr: str | None = None
    mt_filter_dst_addr: str | None = None
    mt_filter_content: str | None = None
    # SMPP Server credentials (None = omit, Jasmin uses its own default of True)
    smpps_allow_bind: bool | None = None
    smpps_max_bindings: int | None = None
    smpps_quota_sms_count: int | None = None
    smpps_throughput: float | None = None


class UserUpdate(BaseModel):
    gid: str | None = None
    password: str | None = None
    mt_throughput: float | None = None
    mo_throughput: float | None = None
    balance: float | None = None
    sms_count: int | None = None
    mt_auth_priority: bool | None = None
    mt_auth_validity_period: bool | None = None
    mt_auth_src_addr: bool | None = None
    mt_auth_schedule_at: bool | None = None
    mt_auth_dlr_level: bool | None = None
    mt_auth_long_content: bool | None = None
    mt_filter_src_addr: str | None = None
    mt_filter_dst_addr: str | None = None
    mt_filter_content: str | None = None
    smpps_allow_bind: bool | None = None
    smpps_max_bindings: int | None = None
    smpps_quota_sms_count: int | None = None
    smpps_throughput: float | None = None


class UserStatusUpdate(BaseModel):
    enabled: bool


class UserOut(BaseModel):
    uid: str
    gid: str
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
