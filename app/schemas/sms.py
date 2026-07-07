from typing import Literal

from pydantic import BaseModel, Field


class SmsSendRequest(BaseModel):
    username: str
    password: str
    to: str = Field(..., description="Destination number E.164")
    content: str
    sender: str | None = Field(default=None, alias="from")
    coding: int = 0
    dlr: Literal["yes", "no"] = "no"
    dlr_url: str | None = None
    dlr_level: int | None = None
    dlr_method: Literal["GET", "POST"] | None = None
    dlr_params: dict[str, str | int | float] | None = Field(
        default=None,
        description="Params que se concatenan a la URL de DLR centralizada (ej. {\"org_id\": 12}). Solo aplica si el DLR está centralizado en el gateway.",
    )
    priority: int | None = Field(default=None, ge=0, le=3)
    schedule_delivery_time: str | None = None
    validity_period: str | None = None
    tags: list[int] = []

    model_config = {"populate_by_name": True}


class SmsBinaryRequest(BaseModel):
    username: str
    password: str
    to: str
    hex_content: str
    coding: int = 1
    sender: str | None = Field(default=None, alias="from")
    dlr: Literal["yes", "no"] = "no"
    dlr_url: str | None = None
    dlr_level: int | None = None
    dlr_method: Literal["GET", "POST"] | None = None
    dlr_params: dict[str, str | int | float] | None = Field(
        default=None,
        description="Params que se concatenan a la URL de DLR centralizada (ej. {\"org_id\": 12}). Solo aplica si el DLR está centralizado en el gateway.",
    )

    model_config = {"populate_by_name": True}


class SmsSendOut(BaseModel):
    message_id: str


class SmsRateOut(BaseModel):
    rate: float
    unit: str = "per_message"
    connector_id: str | None = None


class SmsBalanceOut(BaseModel):
    balance: float | None = None
    sms_count: int | None = None
