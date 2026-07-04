from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.validators import validate_no_control_chars

# Routes define how messages are dispatched to connectors.
# MT routes: outbound — from Jasmin to an SMSC via an SMPP connector.
# MO routes: inbound — from an SMSC to an HTTP connector.
#
# Routes are evaluated in ascending order (lower order number = higher priority).
# DefaultRoute (order 0) is the fallback if no other route matches.
#
# Connector ID syntax when referencing connectors in routes:
#   SMPP connectors: "smppc(<cid>)"  — e.g. "smppc(carrier_mx)"
#   HTTP connectors: "http(<cid>)"   — e.g. "http(webhook_crm)"
#   SMPP server:     "smpps(<cid>)"  — for server-side bindings


MtRouteType = Literal[
    "DefaultRoute",              # catch-all fallback; no filters needed; always at order 0
    "StaticMTRoute",             # single connector; requires at least one filter
    "RandomRoundrobinMTRoute",   # distributes across multiple connectors randomly
    "FailoverMTRoute",           # tries connectors in order; falls back on failure
]

MoRouteType = Literal[
    "DefaultRoute",              # catch-all fallback; no filters needed; always at order 0
    "StaticMORoute",             # single connector; requires at least one filter
    "RandomRoundrobinMORoute",   # distributes across multiple HTTP/SMPP connectors randomly
    "FailoverMORoute",           # tries connectors in order; falls back on failure
]

# Multi-connector route types (use 'connectors' plural key in jcli)
MT_MULTI_CONNECTOR_TYPES = ("RandomRoundrobinMTRoute", "FailoverMTRoute")
MO_MULTI_CONNECTOR_TYPES = ("RandomRoundrobinMORoute", "FailoverMORoute")


class MtRouteCreate(BaseModel):
    type: MtRouteType = Field(
        ...,
        description=(
            "Route type. DefaultRoute is the fallback (order forced to 0 by Jasmin). "
            "StaticMTRoute requires filters. RandomRoundrobinMTRoute uses multiple connectors."
        ),
    )
    order: int = Field(
        ...,
        ge=0,
        description=(
            "Evaluation priority. Lower = higher priority. "
            "DefaultRoute is always stored at order 0 by Jasmin regardless of this value."
        ),
    )
    connectors: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Connector IDs with prefix. Use smppc(<cid>) for SMPP. "
            "RandomRoundrobinMTRoute and FailoverMTRoute accept multiple entries. "
            "Example: [\"smppc(carrier_mx)\"]"
        ),
    )
    filters: list[str] = Field(
        default=[],
        description=(
            "Filter FIDs to match. Required for StaticMTRoute. "
            "If empty and the route type requires filters, Jasmin will use a TransparentFilter "
            "automatically (if one exists). "
            "Example: [\"filter_kenya_src\"]"
        ),
    )
    rate: float | None = Field(
        default=None,
        description=(
            "Per-message cost charged to the user's balance. "
            "0.0 = free. None defaults to 0.0. Example: 0.05"
        ),
    )

    @field_validator("connectors")
    @classmethod
    def validate_connectors(cls, v: list[str]) -> list[str]:
        for item in v:
            validate_no_control_chars(item, "connectors")
        return v

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str]) -> list[str]:
        for item in v:
            validate_no_control_chars(item, "filters")
        return v


class MtRouteUpdate(BaseModel):
    # Route has no update command in Jasmin; it is deleted and recreated internally.
    connectors: list[str] | None = Field(
        default=None,
        description="Replace connector list. If omitted, existing connectors are reused.",
    )
    filters: list[str] | None = Field(
        default=None,
        description=(
            "Replace filter list. "
            "If omitted and current route uses a TransparentFilter, it is auto-resolved. "
            "If the current route uses non-transparent filters, this field is required."
        ),
    )
    rate: float | None = Field(default=None, description="New per-message cost.")

    @field_validator("connectors")
    @classmethod
    def validate_connectors(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                validate_no_control_chars(item, "connectors")
        return v

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                validate_no_control_chars(item, "filters")
        return v


class MtRouteOut(BaseModel):
    order: int
    type: str
    connectors: list[str]
    filters: list[str]  # always [] in response — filter FIDs are not recoverable from Jasmin show output
    rate: float | None = None


class MoRouteCreate(BaseModel):
    type: MoRouteType = Field(
        ...,
        description=(
            "Route type. DefaultRoute is the fallback (order forced to 0). "
            "StaticMORoute requires filters. "
            "RandomRoundrobinMORoute/FailoverMORoute require multiple connectors via 'connectors'."
        ),
    )
    order: int = Field(..., ge=0, description="Evaluation priority. Lower = higher priority.")
    connector: str | None = Field(
        default=None,
        description=(
            "Single connector ID with prefix. For DefaultRoute and StaticMORoute. "
            "Use http(<cid>) or smpps(<cid>). Example: \"http(webhook_crm)\""
        ),
    )
    connectors: list[str] | None = Field(
        default=None,
        description=(
            "Multiple connector IDs for RandomRoundrobinMORoute and FailoverMORoute. "
            "Use http(<cid>) or smpps(<cid>). Example: [\"http(wh1)\", \"http(wh2)\"]"
        ),
    )
    filters: list[str] = Field(
        default=[],
        description=(
            "Filter FIDs to match. Required for StaticMORoute and multi-connector types. "
            "Auto-resolved to TransparentFilter if empty."
        ),
    )

    @model_validator(mode="after")
    def validate_connector_fields(self) -> "MoRouteCreate":
        if self.type in MO_MULTI_CONNECTOR_TYPES:
            if not self.connectors:
                raise ValueError(f"{self.type} requires 'connectors' (list of connector IDs)")
        else:
            if not self.connector:
                raise ValueError(f"{self.type} requires 'connector' (single connector ID)")
        return self

    @field_validator("connector")
    @classmethod
    def validate_connector(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, "connector")
        return v

    @field_validator("connectors")
    @classmethod
    def validate_connectors(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                validate_no_control_chars(item, "connectors")
        return v

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str]) -> list[str]:
        for item in v:
            validate_no_control_chars(item, "filters")
        return v


class MoRouteUpdate(BaseModel):
    connector: str | None = Field(
        default=None,
        description="New single connector ID. For DefaultRoute and StaticMORoute.",
    )
    connectors: list[str] | None = Field(
        default=None,
        description="New connector list. For RandomRoundrobinMORoute and FailoverMORoute.",
    )
    filters: list[str] | None = Field(
        default=None,
        description=(
            "Replace filter list. Required if current route uses non-transparent filters."
        ),
    )

    @field_validator("connector")
    @classmethod
    def validate_connector(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, "connector")
        return v

    @field_validator("connectors")
    @classmethod
    def validate_connectors(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                validate_no_control_chars(item, "connectors")
        return v

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                validate_no_control_chars(item, "filters")
        return v


class MoRouteOut(BaseModel):
    order: int
    type: str
    connector: str | None = None       # populated for single-connector types
    connectors: list[str] = []         # populated for multi-connector types
    filters: list[str]  # always [] — filter FIDs are not recoverable from Jasmin
