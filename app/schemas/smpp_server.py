from pydantic import BaseModel


class SmppServerOut(BaseModel):
    host: str
    port: int
    max_bindings: int | None = None
