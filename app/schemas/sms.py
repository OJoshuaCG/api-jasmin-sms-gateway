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
