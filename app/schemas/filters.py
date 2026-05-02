from typing import Any, Literal

from pydantic import BaseModel, Field

FilterType = Literal[
    "TransparentFilter",
    "ConnectorFilter",
    "UserFilter",
    "GroupFilter",
    "SrcAddrFilter",
    "DstAddrFilter",
    "ShortMessageFilter",
    "DateIntervalFilter",
    "TimeIntervalFilter",
    "DayFilter",
    "EvalPyFilter",
    "TagFilter",
]


class FilterCreate(BaseModel):
    fid: str = Field(..., min_length=1, max_length=64)
    type: FilterType
    params: dict[str, Any] = {}


class FilterUpdate(BaseModel):
    type: FilterType
    params: dict[str, Any] = {}


class FilterOut(BaseModel):
    fid: str
    type: str
    params: dict[str, Any] = {}
