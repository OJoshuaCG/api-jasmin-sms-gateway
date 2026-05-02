from pydantic import BaseModel, Field


class SmppServerUpdate(BaseModel):
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    max_bindings: int | None = None


class SmppServerOut(BaseModel):
    host: str
    port: int
    max_bindings: int | None = None
