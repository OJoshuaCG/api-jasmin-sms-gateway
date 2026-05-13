from typing import Any, Literal

from pydantic import BaseModel, Field

# Filters are reusable conditions attached to routes and interceptors.
# They decide which messages a route/interceptor handles.
# Each filter type inspects a different message attribute.

FilterType = Literal[
    "TransparentFilter",      # matches all messages — use as a catch-all
    "ConnectorFilter",        # matches by originating SMPP connector ID
    "UserFilter",             # matches by Jasmin user UID
    "GroupFilter",            # matches by Jasmin group GID
    "SourceAddrFilter",       # matches source address by regex
    "DestinationAddrFilter",  # matches destination address by regex
    "ShortMessageFilter",     # matches message text by regex
    "DateIntervalFilter",     # matches if current date is within a range
    "TimeIntervalFilter",     # matches if current time is within a range
    "EvalPyFilter",           # executes arbitrary Python to decide match
    "TagFilter",              # matches by numeric tag attached to message
]

# Required params by filter type:
# TransparentFilter    — none
# ConnectorFilter      — cid: str  (e.g. "smppc1")
# UserFilter           — uid: str  (e.g. "user01")
# GroupFilter          — gid: str  (e.g. "premium")
# SourceAddrFilter     — source_addr: str  (regex, e.g. "^254")
# DestinationAddrFilter— destination_addr: str  (regex, e.g. "^\\+1")
# ShortMessageFilter   — short_message: str  (regex, e.g. "^STOP")
# DateIntervalFilter   — dateInterval: str  ("YYYY-MM-DD;YYYY-MM-DD", e.g. "2024-01-01;2024-12-31")
# TimeIntervalFilter   — timeInterval: str  ("HH:MM:SS;HH:MM:SS", e.g. "08:00:00;18:00:00")
# EvalPyFilter         — pyCode: str  (Python expression returning True/False, e.g. "routable.pdu.params['source_addr'].startswith('254')")
# TagFilter            — tag: int  (e.g. 99)


class FilterCreate(BaseModel):
    fid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Unique filter identifier. Referenced by routes and interceptors. "
            "Example: \"filter_kenya_src\""
        ),
    )
    type: FilterType = Field(
        ...,
        description="Filter type. Determines which message attribute is inspected.",
    )
    params: dict[str, Any] = Field(
        default={},
        description=(
            "Type-specific parameters. See FilterType comments for required keys per type. "
            "Example for SourceAddrFilter: {\"source_addr\": \"^254\"}"
        ),
    )


class FilterUpdate(BaseModel):
    type: FilterType = Field(..., description="New filter type (filter is deleted and recreated).")
    params: dict[str, Any] = Field(
        default={},
        description="New parameters for the updated filter type.",
    )


class FilterOut(BaseModel):
    fid: str
    type: str
    params: dict[str, Any] = {}
