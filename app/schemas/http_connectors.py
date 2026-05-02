from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class HttpConnectorCreate(BaseModel):
    cid: str = Field(..., min_length=1, max_length=64)
    url: str
    method: Literal["GET", "POST"]


class HttpConnectorUpdate(BaseModel):
    url: str | None = None
    method: Literal["GET", "POST"] | None = None


class HttpConnectorOut(BaseModel):
    cid: str
    url: str
    method: str
