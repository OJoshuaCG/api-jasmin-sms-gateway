from fastapi import APIRouter

from app.controllers.insights_controller import InsightsController
from app.schemas.insights import (
    ActiveSessionsOut,
    GroupMembersOut,
    OverviewOut,
    RouteMapOut,
    SmppConnectorDetailOut,
    SmppConnectorUsageOut,
    SmppConnectorsHealthOut,
    UserProfileOut,
)
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get(
    "/overview",
    response_model=ApiResponse[OverviewOut],
    summary="System overview",
    description=(
        "Returns entity counts for every Jasmin resource (users, groups, connectors, routes, "
        "filters, interceptors) and the current health status of both the Telnet and HTTP interfaces. "
        "Designed as a single dashboard call."
    ),
)
async def overview():
    return success(data=await InsightsController().overview())


@router.get(
    "/users/{uid}/profile",
    response_model=ApiResponse[UserProfileOut],
    summary="Complete user profile",
    description=(
        "Returns the full profile of a Jasmin user in a single call: user configuration, "
        "the group it belongs to, and real-time activity stats (SMPP binds, HTTP requests, "
        "submit counts). Useful for user detail pages in admin UIs."
    ),
)
async def user_profile(uid: str):
    return success(data=await InsightsController().user_profile(uid))


@router.get(
    "/groups/{gid}/members",
    response_model=ApiResponse[GroupMembersOut],
    summary="Group members with activity",
    description=(
        "Returns the group configuration and all users that belong to it, enriched with "
        "real-time activity stats (active SMPP binds, HTTP request counts). "
        "Useful for group detail pages and auditing who is actively using each group."
    ),
)
async def group_members(gid: str):
    return success(data=await InsightsController().group_members(gid))


@router.get(
    "/connectors/smpp/health",
    response_model=ApiResponse[SmppConnectorsHealthOut],
    summary="SMPP connectors health dashboard",
    description=(
        "Returns all SMPP connectors with their current operational status and aggregated "
        "submit/error stats in a single call. Combines smppccm status with stats --smppcs. "
        "Includes summary counts: total connectors, currently connected, and those with errors. "
        "Designed for monitoring dashboards and alerting."
    ),
)
async def connectors_health():
    return success(data=await InsightsController().connectors_health())


@router.get(
    "/connectors/smpp/{cid}/detail",
    response_model=ApiResponse[SmppConnectorDetailOut],
    summary="SMPP connector full detail",
    description=(
        "Returns the complete view of an SMPP connector in a single call: full configuration "
        "(host, port, TON/NPI, throughput), current operational status (started/stopped/bound, "
        "active sessions), and historical stats (submit counts, error counts, timestamps). "
        "Useful for connector detail pages in admin UIs."
    ),
)
async def connector_detail(cid: str):
    return success(data=await InsightsController().connector_detail(cid))


@router.get(
    "/connectors/smpp/{cid}/usage",
    response_model=ApiResponse[SmppConnectorUsageOut],
    summary="SMPP connector route usage",
    description=(
        "Returns the SMPP connector configuration and all MT routes that reference it. "
        "Useful for understanding the blast radius before modifying or deleting a connector, "
        "and for visualizing which routes depend on each carrier."
    ),
)
async def smpp_connector_usage(cid: str):
    return success(data=await InsightsController().smpp_connector_usage(cid))


@router.get(
    "/sessions/active",
    response_model=ApiResponse[ActiveSessionsOut],
    summary="Active sessions snapshot",
    description=(
        "Real-time snapshot of all active connections: users currently bound via SMPP "
        "(smpp_bound_connections > 0), SMPP connectors that are started or actively connected "
        "to a carrier, and the global SMPP server API stats. "
        "Designed for live monitoring dashboards and NOC views."
    ),
)
async def active_sessions():
    return success(data=await InsightsController().active_sessions())


@router.get(
    "/routes/map",
    response_model=ApiResponse[RouteMapOut],
    summary="Full route topology map",
    description=(
        "Returns all MT and MO routes with their target connectors and filter indicators "
        "in a single call. The filter_indicator field shows the raw Jasmin filter string "
        "(e.g. '<T>' for TransparentFilter). Designed to power routing topology visualizations."
    ),
)
async def route_map():
    return success(data=await InsightsController().route_map())
