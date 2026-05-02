from pydantic import BaseModel


class TelnetStatus(BaseModel):
    connected: bool
    uptime_seconds: float | None = None
    reconnecting: bool = False


class JasminHttpStatus(BaseModel):
    reachable: bool


class HealthOut(BaseModel):
    status: str
    telnet: TelnetStatus
    jasmin_http: JasminHttpStatus


class SessionOut(BaseModel):
    connected: bool
    reconnecting: bool
    uptime_seconds: float | None = None
    host: str
    port: int
