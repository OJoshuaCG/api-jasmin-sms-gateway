from typing import Literal

from pydantic import BaseModel, Field

MtRouteType = Literal[
    "DefaultRoute",
    "StaticMTRoute",
    "RandomRoundrobinMTRoute",
    "LeastCostMTRoute",
]

MoRouteType = Literal["DefaultRoute", "StaticMORoute"]


class MtRouteCreate(BaseModel):
    type: MtRouteType
    order: int = Field(..., ge=0)
    connectors: list[str] = Field(..., min_length=1)
    filters: list[str] = []
    rate: float | None = None


class MtRouteUpdate(BaseModel):
    connectors: list[str] | None = None
    filters: list[str] | None = None
    rate: float | None = None


class MtRouteOut(BaseModel):
    order: int
    type: str
    connectors: list[str]
    filters: list[str]
    rate: float | None = None


class MoRouteCreate(BaseModel):
    type: MoRouteType
    order: int = Field(..., ge=0)
    connector: str
    filters: list[str] = []


class MoRouteUpdate(BaseModel):
    connector: str | None = None
    filters: list[str] | None = None


class MoRouteOut(BaseModel):
    order: int
    type: str
    connector: str
    filters: list[str]
