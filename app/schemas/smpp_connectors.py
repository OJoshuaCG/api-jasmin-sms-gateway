from typing import Literal

from pydantic import BaseModel, Field, FieldValidationInfo, field_validator

from app.utils.validators import validate_identifier, validate_no_control_chars

# SMPP connectors represent outbound connections from Jasmin to an SMSC (carrier/aggregator).
# Jasmin uses these to deliver MT (mobile-terminated) messages to the carrier.
# After creation, start/stop the connector to begin/end the SMPP session.


class SmppConnectorCreate(BaseModel):
    cid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Unique connector ID. Used to reference this connector in routes. "
            "Only letters, digits, underscores and hyphens allowed. "
            "Example: \"carrier_mx\""
        ),
    )

    @field_validator("cid")
    @classmethod
    def validate_cid(cls, v: str) -> str:
        return validate_identifier(v, "cid")

    @field_validator("host", "username", "password")
    @classmethod
    def validate_string_fields(cls, v: str, info: FieldValidationInfo) -> str:
        return validate_no_control_chars(v, info.field_name)

    @field_validator("system_type", "address_range")
    @classmethod
    def validate_optional_string_fields(cls, v: str | None, info: FieldValidationInfo) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, info.field_name)
        return v
    host: str = Field(
        ...,
        description="SMSC hostname or IP address. Example: \"smpp.carrier.com\"",
    )
    port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="SMSC TCP port. Standard SMPP port is 2775. Example: 2775",
    )
    # SMPP 3.4 protocol limits: system_id=15, password=8 (C-string buffers minus null terminator)
    username: str = Field(
        ...,
        min_length=1,
        max_length=15,
        description="SMPP system_id for authentication. Max 15 chars per SMPP 3.4 spec.",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=8,
        description="SMPP password for authentication. Max 8 chars per SMPP 3.4 spec.",
    )
    bind_to: Literal["transceiver", "transmitter", "receiver"] = Field(
        default="transceiver",
        description=(
            "SMPP bind type (jcli key: 'bind'). "
            "transceiver: send and receive (recommended). "
            "transmitter: send only. receiver: receive only."
        ),
    )
    system_type: str | None = Field(
        default=None,
        max_length=12,
        description=(
            "SMPP system_type field sent during bind. Carrier-specific, often empty. "
            "Example: \"OTA\""
        ),
    )
    address_range: str | None = Field(
        default=None,
        max_length=40,
        description=(
            "Address range for the bind (SMPP address_range field). "
            "Usually empty; some carriers require it. Example: \"^254\""
        ),
    )
    # TON: 0=Unknown,1=International,2=National,3=Network,4=Subscriber,5=Alphanumeric,6=Abbreviated
    source_addr_ton: int | None = Field(
        default=None,
        ge=0,
        le=6,
        description=(
            "Type of Number for source address override. "
            "0=Unknown, 1=International, 5=Alphanumeric. "
            "None = use Jasmin default."
        ),
    )
    # NPI: 0=Unknown,1=ISDN,3=Data,4=Telex,6=Land Mobile,8=National,9=Private,10=ERMES,14=Internet,18=WAP
    source_addr_npi: int | None = Field(
        default=None,
        ge=0,
        le=18,
        description="Numbering Plan Indicator for source address. 0=Unknown, 1=ISDN/E.164.",
    )
    dest_addr_ton: int | None = Field(
        default=None,
        ge=0,
        le=6,
        description="TON for destination address. Typically 1 (International) for MSISDN.",
    )
    dest_addr_npi: int | None = Field(
        default=None,
        ge=0,
        le=18,
        description="NPI for destination address. Typically 1 (ISDN/E.164) for MSISDN.",
    )
    submit_throughput: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Max submit_sm messages per second Jasmin sends to the SMSC. "
            "None = unlimited. Example: 50.0"
        ),
    )
    dlr_expiry: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Seconds to wait for a DLR (delivery receipt) before expiring. "
            "None = Jasmin default. Example: 86400 (24 hours)"
        ),
    )
    reconnect_on_connection_loss: bool | None = Field(default=None, description="Auto-reconnect if the SMPP session drops. Default: True.")
    reconnect_on_connection_loss_delay: int | None = Field(default=None, description="Seconds to wait before reconnecting after a session drop. Default: 10.")
    reconnect_on_connection_failure: bool | None = Field(default=None, description="Auto-retry if the initial connection fails. Default: True.")
    reconnect_on_connection_failure_delay: int | None = Field(default=None, description="Seconds to wait before retrying a failed connection. Default: 10.")

    # Connection timeouts (jcli keys confirmed via smppccm -s and interactive probe)
    bind_timeout: int | None = Field(default=None, ge=0, description="Bind request timeout in seconds (jcli: bind_to). Default: 30.")
    elink_interval: int | None = Field(default=None, ge=0, description="Enquire-link keepalive interval in seconds. Default: 30.")
    res_to: int | None = Field(default=None, ge=0, description="Response timeout in seconds. Default: 120.")
    pdu_red_to: int | None = Field(default=None, ge=0, description="PDU inactivity redirect timeout in seconds. Default: 10.")
    trx_to: int | None = Field(default=None, ge=0, description="TRX session inactivity timeout in seconds. Default: 300.")
    requeue_delay: int | None = Field(default=None, ge=0, description="Seconds to wait before re-queueing a failed message. Default: 120.")

    # Message encoding / routing
    coding: int | None = Field(
        default=None, ge=0, le=255,
        description="Data coding scheme. 0=default GSM7, 1=IA5/ASCII, 3=Latin-1, 8=UCS-2. Default: 0.",
    )
    dlr_msgid: int | None = Field(
        default=None, ge=0, le=2,
        description="Which PDU field carries the message ID in DLR receipts. 0=smpp msgid, 1=receipted_msgid. Default: 0.",
    )

    # TLS
    ssl: bool | None = Field(default=None, description="Enable TLS for the SMPP connection. Default: False.")


class SmppConnectorUpdate(BaseModel):
    # All fields optional — only provided fields are updated.
    host: str | None = Field(default=None, description="New SMSC host.")
    port: int | None = Field(default=None, ge=1, le=65535, description="New SMSC port.")
    username: str | None = Field(default=None, min_length=1, max_length=15, description="New SMPP system_id.")
    password: str | None = Field(default=None, min_length=1, max_length=8, description="New SMPP password.")
    bind_to: Literal["transceiver", "transmitter", "receiver"] | None = Field(default=None, description="New bind type.")
    system_type: str | None = Field(default=None, max_length=12, description="New system_type.")
    address_range: str | None = Field(default=None, max_length=40, description="New address range.")

    @field_validator("host", "username", "password", "system_type", "address_range")
    @classmethod
    def validate_string_fields(cls, v: str | None, info: FieldValidationInfo) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, info.field_name)
        return v
    source_addr_ton: int | None = Field(default=None, ge=0, le=6, description="New source TON.")
    source_addr_npi: int | None = Field(default=None, ge=0, le=18, description="New source NPI.")
    dest_addr_ton: int | None = Field(default=None, ge=0, le=6, description="New destination TON.")
    dest_addr_npi: int | None = Field(default=None, ge=0, le=18, description="New destination NPI.")
    submit_throughput: float | None = Field(default=None, ge=0, description="New throughput limit.")
    dlr_expiry: int | None = Field(default=None, ge=0, description="New DLR expiry seconds.")
    reconnect_on_connection_loss: bool | None = Field(default=None, description="Update reconnect-on-loss.")
    reconnect_on_connection_loss_delay: int | None = Field(default=None, description="Update reconnect-on-loss delay.")
    reconnect_on_connection_failure: bool | None = Field(default=None, description="Update reconnect-on-failure.")
    reconnect_on_connection_failure_delay: int | None = Field(default=None, description="Update reconnect-on-failure delay.")
    bind_timeout: int | None = Field(default=None, ge=0, description="New bind timeout (jcli: bind_to).")
    elink_interval: int | None = Field(default=None, ge=0, description="New enquire-link interval.")
    res_to: int | None = Field(default=None, ge=0, description="New response timeout.")
    pdu_red_to: int | None = Field(default=None, ge=0, description="New PDU inactivity timeout.")
    trx_to: int | None = Field(default=None, ge=0, description="New TRX session timeout.")
    requeue_delay: int | None = Field(default=None, ge=0, description="New requeue delay.")
    coding: int | None = Field(default=None, ge=0, le=255, description="New data coding scheme.")
    dlr_msgid: int | None = Field(default=None, ge=0, le=2, description="New DLR message ID field.")
    ssl: bool | None = Field(default=None, description="Update TLS setting.")


class SmppConnectorOut(BaseModel):
    cid: str
    host: str
    port: int
    username: str
    bind_to: str
    system_type: str | None = None
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
    bind_timeout: int | None = None
    elink_interval: int | None = None
    res_to: int | None = None
    pdu_red_to: int | None = None
    trx_to: int | None = None
    requeue_delay: int | None = None
    coding: int | None = None
    dlr_msgid: int | None = None
    ssl: bool = False


class SmppConnectorStatusOut(BaseModel):
    cid: str
    status: str          # "started", "stopped", "connecting", "bound_TRX", etc.
    sessions_count: int = 0
    last_error: str | None = None
