from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    gid: str = Field(..., min_length=1, max_length=64)


class GroupUpdate(BaseModel):
    enabled: bool


class GroupOut(BaseModel):
    gid: str
    enabled: bool
