from typing import Literal

from pydantic import BaseModel, Field, field_validator

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
    "LeastCostMTRoute",          # NOT DOCUMENTED — reserved for future use
]

MoRouteType = Literal[
    "DefaultRoute",   # catch-all fallback; no filters needed; always at order 0
    "StaticMORoute",  # single connector; requires at least one filter
]


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
            "StaticMORoute requires filters."
        ),
    )
    order: int = Field(
        ...,
        ge=0,
        description="Evaluation priority. Lower = higher priority.",
    )
    connector: str = Field(
        ...,
        description=(
            "HTTP connector ID with prefix. Use http(<cid>) for HTTP connectors. "
            "Example: \"http(webhook_crm)\""
        ),
    )
    filters: list[str] = Field(
        default=[],
        description=(
            "Filter FIDs to match. Required for StaticMORoute. "
            "Auto-resolved to TransparentFilter if empty and route type requires filters. "
            "Example: [\"filter_short_code\"]"
        ),
    )

    @field_validator("connector")
    @classmethod
    def validate_connector(cls, v: str) -> str:
        return validate_no_control_chars(v, "connector")

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str]) -> list[str]:
        for item in v:
            validate_no_control_chars(item, "filters")
        return v


class MoRouteUpdate(BaseModel):
    connector: str | None = Field(
        default=None,
        description="New HTTP connector ID. If omitted, existing connector is reused.",
    )
    filters: list[str] | None = Field(
        default=None,
        description=(
            "Replace filter list. Required if current route uses non-transparent filters "
            "and connector is being changed."
        ),
    )

    @field_validator("connector")
    @classmethod
    def validate_connector(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, "connector")
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
    connector: str
    filters: list[str]  # always [] in response — filter FIDs are not recoverable from Jasmin
