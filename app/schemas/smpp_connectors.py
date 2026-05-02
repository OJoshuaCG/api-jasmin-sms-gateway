from typing import Literal

from pydantic import BaseModel, Field


class SmppConnectorCreate(BaseModel):
    cid: str = Field(..., min_length=1, max_length=64)
    host: str
    port: int = Field(..., ge=1, le=65535)
    # SMPP 3.4 protocol limits: system_id=15, password=8 (C-string buffers minus null terminator)
    username: str = Field(..., min_length=1, max_length=15)
    password: str = Field(..., min_length=1, max_length=8)
    bind_to: Literal["transceiver", "transmitter", "receiver"] = "transceiver"
    system_type: str | None = Field(default=None, max_length=12)
    interface_version: Literal["33", "34"] = "34"
    address_range: str | None = Field(default=None, max_length=40)
    # TON: 0=Unknown,1=International,2=National,3=Network,4=Subscriber,5=Alphanumeric,6=Abbreviated
    source_addr_ton: int | None = Field(default=None, ge=0, le=6)
    # NPI: 0=Unknown,1=ISDN,3=Data,4=Telex,6=Land Mobile,8=National,9=Private,10=ERMES,14=Internet,18=WAP
    source_addr_npi: int | None = Field(default=None, ge=0, le=18)
    dest_addr_ton: int | None = Field(default=None, ge=0, le=6)
    dest_addr_npi: int | None = Field(default=None, ge=0, le=18)
    submit_throughput: float | None = Field(default=None, ge=0)
    dlr_expiry: int | None = Field(default=None, ge=0)
    reconnect_on_connection_loss: bool | None = None
    reconnect_on_connection_loss_delay: int | None = None
    reconnect_on_connection_failure: bool | None = None
    reconnect_on_connection_failure_delay: int | None = None


class SmppConnectorUpdate(BaseModel):
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, min_length=1, max_length=15)
    password: str | None = Field(default=None, min_length=1, max_length=8)
    bind_to: Literal["transceiver", "transmitter", "receiver"] | None = None
    system_type: str | None = Field(default=None, max_length=12)
    interface_version: Literal["33", "34"] | None = None
    address_range: str | None = Field(default=None, max_length=40)
    source_addr_ton: int | None = Field(default=None, ge=0, le=6)
    source_addr_npi: int | None = Field(default=None, ge=0, le=18)
    dest_addr_ton: int | None = Field(default=None, ge=0, le=6)
    dest_addr_npi: int | None = Field(default=None, ge=0, le=18)
    submit_throughput: float | None = Field(default=None, ge=0)
    dlr_expiry: int | None = Field(default=None, ge=0)
    reconnect_on_connection_loss: bool | None = None
    reconnect_on_connection_loss_delay: int | None = None
    reconnect_on_connection_failure: bool | None = None
    reconnect_on_connection_failure_delay: int | None = None


class SmppConnectorOut(BaseModel):
    cid: str
    host: str
    port: int
    username: str
    bind_to: str
    system_type: str | None = None
    interface_version: str = "34"
    address_range: str | None = None
    source_addr_ton: int | None = None
    source_addr_npi: int | None = None
    dest_addr_ton: int | None = None
    dest_addr_npi: int | None = None
    submit_throughput: float | None = None
    dlr_expiry: int | None = None
    reconnect_on_connection_loss: bool = True
    reconnect_on_connection_loss_delay: int = 10
    reconnect_on_connection_failure: bool = True
    reconnect_on_connection_failure_delay: int = 10


class SmppConnectorStatusOut(BaseModel):
    cid: str
    status: str
    sessions_count: int = 0
    last_error: str | None = None
