from pydantic import BaseModel

from app.schemas.groups import GroupOut
from app.schemas.smpp_connectors import SmppConnectorOut, SmppConnectorStatusOut
from app.schemas.stats import SmppConnectorStatsOut, SmppServerApiStatsOut, UserStatsOut
from app.schemas.users import UserOut


# ── Overview ────────────────────────────────────────────────────────────────

class OverviewCounts(BaseModel):
    users: int
    groups: int
    smpp_connectors: int
    http_connectors: int
    mt_routes: int
    mo_routes: int
    filters: int
    mt_interceptors: int
    mo_interceptors: int


class OverviewOut(BaseModel):
    status: str
    telnet_connected: bool
    jasmin_http_reachable: bool
    counts: OverviewCounts


# ── User profile ─────────────────────────────────────────────────────────────

class UserProfileOut(BaseModel):
    user: UserOut
    group: GroupOut | None = None
    stats: UserStatsOut | None = None


# ── SMPP connector usage (which MT routes use it) ────────────────────────────

class ConnectorRouteRef(BaseModel):
    order: int
    type: str
    rate: float | None = None


class SmppConnectorUsageOut(BaseModel):
    cid: str
    connector: SmppConnectorOut
    mt_routes: list[ConnectorRouteRef]
    mt_routes_count: int


# ── Route topology map ───────────────────────────────────────────────────────

class MtRouteMapEntry(BaseModel):
    order: int
    type: str
    connectors: list[str]
    filter_indicator: str
    rate: float | None = None


class MoRouteMapEntry(BaseModel):
    order: int
    type: str
    connector: str
    filter_indicator: str


class RouteMapOut(BaseModel):
    mt_routes: list[MtRouteMapEntry]
    mo_routes: list[MoRouteMapEntry]
    total_mt: int
    total_mo: int


# ── SMPP connector full detail (config + status + stats) ─────────────────────

class SmppConnectorDetailOut(BaseModel):
    connector: SmppConnectorOut
    status: SmppConnectorStatusOut
    stats: SmppConnectorStatsOut | None = None


# ── Group members ────────────────────────────────────────────────────────────

class GroupMemberOut(BaseModel):
    uid: str
    enabled: bool
    smpp_bound_connections: int = 0
    http_request_count: int = 0
    smpp_last_activity: str | None = None
    http_last_activity: str | None = None


class GroupMembersOut(BaseModel):
    group: GroupOut
    members: list[GroupMemberOut]
    total: int


# ── Active sessions ──────────────────────────────────────────────────────────

class ActiveUserSession(BaseModel):
    uid: str
    smpp_bound_connections: int
    smpp_last_activity: str | None = None
    http_request_count: int = 0
    http_last_activity: str | None = None


class ActiveConnectorSession(BaseModel):
    cid: str
    status: str
    sessions_count: int = 0
    bound_at: str | None = None
    submits: str = "0/0"


class ActiveSessionsOut(BaseModel):
    active_users: list[ActiveUserSession]
    active_connectors: list[ActiveConnectorSession]
    smpp_server: SmppServerApiStatsOut
    total_bound_users: int
    total_connected_connectors: int


# ── SMPP connectors health dashboard ─────────────────────────────────────────

class SmppConnectorHealthEntry(BaseModel):
    cid: str
    status: str
    sessions_count: int = 0
    connected_at: str | None = None
    bound_at: str | None = None
    disconnected_at: str | None = None
    submits: str = "0/0"
    delivers: str = "0/0"
    qos_errors: int = 0
    other_errors: int = 0


class SmppConnectorsHealthOut(BaseModel):
    connectors: list[SmppConnectorHealthEntry]
    total: int
    connected: int
    with_errors: int
