from pydantic import BaseModel


class SmppConnectorStatsOut(BaseModel):
    cid: str
    status: str
    sent_count: int = 0
    received_count: int = 0
    error_count: int = 0
    last_activity_at: str | None = None


class UserStatsOut(BaseModel):
    uid: str
    mt_count: int = 0
    mo_count: int = 0
    last_activity_at: str | None = None
