from app.core.jasmin_http import get_jasmin_http_client
from app.core.jasmin_parsers import (
    parse_filter_list,
    parse_group_list,
    parse_httpccm_list,
    parse_interceptor_list,
    parse_mo_route_show,
    parse_mt_route_show,
    parse_route_list,
    parse_smppccm_list,
    parse_stats_smppsapi,
    parse_stats_smppcs,
    parse_stats_users,
    parse_user_list,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.insights import (
    ActiveConnectorSession,
    ActiveSessionsOut,
    ActiveUserSession,
    ConnectorRouteRef,
    GroupMemberOut,
    GroupMembersOut,
    MoRouteMapEntry,
    MtRouteMapEntry,
    OverviewCounts,
    OverviewOut,
    RouteMapOut,
    SmppConnectorDetailOut,
    SmppConnectorHealthEntry,
    SmppConnectorUsageOut,
    SmppConnectorsHealthOut,
    UserProfileOut,
)
from app.schemas.stats import SmppServerApiStatsOut


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


class InsightsController:

    # ── Overview ─────────────────────────────────────────────────────────────

    async def overview(self) -> OverviewOut:
        telnet = _telnet()
        try:
            users_out = await telnet.execute("user --list")
            groups_out = await telnet.execute("group --list")
            smppcs_out = await telnet.execute("smppccm --list")
            httpcs_out = await telnet.execute("httpccm --list")
            mt_routes_out = await telnet.execute("mtrouter --list")
            mo_routes_out = await telnet.execute("morouter --list")
            filters_out = await telnet.execute("filter --list")
            mt_int_out = await telnet.execute("mtinterceptor --list")
            mo_int_out = await telnet.execute("mointerceptor --list")
        except TelnetNotConnectedError as exc:
            _503(exc)

        counts = OverviewCounts(
            users=len(parse_user_list(users_out)),
            groups=len(parse_group_list(groups_out)),
            smpp_connectors=len(parse_smppccm_list(smppcs_out)),
            http_connectors=len(parse_httpccm_list(httpcs_out)),
            mt_routes=len(parse_route_list(mt_routes_out)),
            mo_routes=len(parse_route_list(mo_routes_out)),
            filters=len(parse_filter_list(filters_out)),
            mt_interceptors=len(parse_interceptor_list(mt_int_out)),
            mo_interceptors=len(parse_interceptor_list(mo_int_out)),
        )

        http_reachable = False
        try:
            resp = await get_jasmin_http_client().get("/")
            http_reachable = resp.status_code < 500
        except Exception:
            pass

        if telnet.is_connected and http_reachable:
            status = "ok"
        elif telnet.is_connected or http_reachable:
            status = "degraded"
        else:
            status = "error"

        return OverviewOut(
            status=status,
            telnet_connected=telnet.is_connected,
            jasmin_http_reachable=http_reachable,
            counts=counts,
        )

    # ── User profile ──────────────────────────────────────────────────────────

    async def user_profile(self, uid: str) -> UserProfileOut:
        from app.controllers.groups_controller import GroupsController
        from app.controllers.stats_controller import StatsController
        from app.controllers.users_controller import UsersController

        user = await UsersController().get_user(uid)

        group = None
        try:
            group = await GroupsController().get_group(user.gid)
        except AppHttpException:
            pass

        stats = None
        try:
            stats = await StatsController().get_user_stats(uid)
        except AppHttpException:
            pass

        return UserProfileOut(user=user, group=group, stats=stats)

    # ── SMPP connector usage ──────────────────────────────────────────────────

    async def smpp_connector_usage(self, cid: str) -> SmppConnectorUsageOut:
        from app.controllers.smpp_connectors_controller import SmppConnectorsController

        connector = await SmppConnectorsController().get_connector(cid)

        telnet = _telnet()
        try:
            list_out = await telnet.execute("mtrouter --list")
        except TelnetNotConnectedError as exc:
            _503(exc)

        rows = parse_route_list(list_out)
        target = f"smppc({cid})"
        matching: list[ConnectorRouteRef] = []

        for row in rows:
            try:
                show_out = await telnet.execute(f"mtrouter -s {row['order']}")
            except TelnetNotConnectedError as exc:
                _503(exc)
            route_data = parse_mt_route_show(show_out, row["order"])
            if target in route_data.get("connectors", []):
                matching.append(ConnectorRouteRef(
                    order=row["order"],
                    type=row["type"],
                    rate=route_data.get("rate"),
                ))

        return SmppConnectorUsageOut(
            cid=cid,
            connector=connector,
            mt_routes=matching,
            mt_routes_count=len(matching),
        )

    # ── Route topology map ────────────────────────────────────────────────────

    async def route_map(self) -> RouteMapOut:
        telnet = _telnet()
        try:
            mt_list_out = await telnet.execute("mtrouter --list")
            mo_list_out = await telnet.execute("morouter --list")
        except TelnetNotConnectedError as exc:
            _503(exc)

        mt_rows = parse_route_list(mt_list_out)
        mo_rows = parse_route_list(mo_list_out)

        mt_entries: list[MtRouteMapEntry] = []
        for row in mt_rows:
            try:
                show_out = await telnet.execute(f"mtrouter -s {row['order']}")
            except TelnetNotConnectedError as exc:
                _503(exc)
            route_data = parse_mt_route_show(show_out, row["order"])
            mt_entries.append(MtRouteMapEntry(
                order=row["order"],
                type=row["type"],
                connectors=route_data.get("connectors", []),
                filter_indicator=row.get("filter_raw", ""),
                rate=route_data.get("rate"),
            ))

        mo_entries: list[MoRouteMapEntry] = []
        for row in mo_rows:
            try:
                show_out = await telnet.execute(f"morouter -s {row['order']}")
            except TelnetNotConnectedError as exc:
                _503(exc)
            route_data = parse_mo_route_show(show_out, row["order"])
            mo_entries.append(MoRouteMapEntry(
                order=row["order"],
                type=row["type"],
                connector=route_data.get("connector", ""),
                filter_indicator=row.get("filter_raw", ""),
            ))

        return RouteMapOut(
            mt_routes=mt_entries,
            mo_routes=mo_entries,
            total_mt=len(mt_entries),
            total_mo=len(mo_entries),
        )

    # ── SMPP connector full detail ────────────────────────────────────────────

    async def connector_detail(self, cid: str) -> SmppConnectorDetailOut:
        from app.controllers.smpp_connectors_controller import SmppConnectorsController
        from app.controllers.stats_controller import StatsController

        connector = await SmppConnectorsController().get_connector(cid)
        status = await SmppConnectorsController().get_connector_status(cid)

        stats = None
        try:
            stats = await StatsController().get_smppccm_stats(cid)
        except AppHttpException:
            pass

        return SmppConnectorDetailOut(connector=connector, status=status, stats=stats)

    # ── Group members ─────────────────────────────────────────────────────────

    async def group_members(self, gid: str) -> GroupMembersOut:
        from app.controllers.groups_controller import GroupsController

        group = await GroupsController().get_group(gid)

        telnet = _telnet()
        try:
            users_out = await telnet.execute("user --list")
            stats_out = await telnet.execute("stats --users")
        except TelnetNotConnectedError as exc:
            _503(exc)

        all_users = parse_user_list(users_out)
        group_users = [u for u in all_users if u["gid"] == gid]

        stats_rows = parse_stats_users(stats_out)
        stats_by_uid = {row["uid"]: row for row in stats_rows}

        members: list[GroupMemberOut] = []
        for u in group_users:
            uid = u["uid"]
            s = stats_by_uid.get(uid, {})
            members.append(GroupMemberOut(
                uid=uid,
                enabled=u["enabled"],
                smpp_bound_connections=s.get("smpp_bound_connections", 0),
                http_request_count=s.get("http_request_count", 0),
                smpp_last_activity=s.get("smpp_last_activity"),
                http_last_activity=s.get("http_last_activity"),
            ))

        return GroupMembersOut(group=group, members=members, total=len(members))

    # ── Active sessions ───────────────────────────────────────────────────────

    async def active_sessions(self) -> ActiveSessionsOut:
        telnet = _telnet()
        try:
            users_stats_out = await telnet.execute("stats --users")
            smppcs_stats_out = await telnet.execute("stats --smppcs")
            connectors_list_out = await telnet.execute("smppccm --list")
            smppsapi_out = await telnet.execute("stats --smppsapi")
        except TelnetNotConnectedError as exc:
            _503(exc)

        users_stats = parse_stats_users(users_stats_out)
        active_users = [
            ActiveUserSession(
                uid=u["uid"],
                smpp_bound_connections=u["smpp_bound_connections"],
                smpp_last_activity=u.get("smpp_last_activity"),
                http_request_count=u.get("http_request_count", 0),
                http_last_activity=u.get("http_last_activity"),
            )
            for u in users_stats
            if u["smpp_bound_connections"] > 0
        ]

        smppcs_stats = parse_stats_smppcs(smppcs_stats_out)
        connectors_list = parse_smppccm_list(connectors_list_out)
        stats_by_cid = {s["cid"]: s for s in smppcs_stats}

        # Active connectors: those with sessions > 0 or status is not "stopped"
        active_connectors: list[ActiveConnectorSession] = []
        for c in connectors_list:
            if c["status"] == "stopped" and c.get("sessions_count", 0) == 0:
                continue
            s = stats_by_cid.get(c["cid"], {})
            active_connectors.append(ActiveConnectorSession(
                cid=c["cid"],
                status=c["status"],
                sessions_count=c.get("sessions_count", 0),
                bound_at=s.get("bound_at"),
                submits=s.get("submits", "0/0"),
            ))

        smpp_server = SmppServerApiStatsOut(**parse_stats_smppsapi(smppsapi_out))

        return ActiveSessionsOut(
            active_users=active_users,
            active_connectors=active_connectors,
            smpp_server=smpp_server,
            total_bound_users=len(active_users),
            total_connected_connectors=len(active_connectors),
        )

    # ── SMPP connectors health ────────────────────────────────────────────────

    async def connectors_health(self) -> SmppConnectorsHealthOut:
        telnet = _telnet()
        try:
            list_out = await telnet.execute("smppccm --list")
            stats_out = await telnet.execute("stats --smppcs")
        except TelnetNotConnectedError as exc:
            _503(exc)

        connectors_list = parse_smppccm_list(list_out)
        stats_list = parse_stats_smppcs(stats_out)
        stats_by_cid = {s["cid"]: s for s in stats_list}

        entries: list[SmppConnectorHealthEntry] = []
        for c in connectors_list:
            s = stats_by_cid.get(c["cid"], {})
            entries.append(SmppConnectorHealthEntry(
                cid=c["cid"],
                status=c["status"],
                sessions_count=c.get("sessions_count", 0),
                connected_at=s.get("connected_at"),
                bound_at=s.get("bound_at"),
                disconnected_at=s.get("disconnected_at"),
                submits=s.get("submits", "0/0"),
                delivers=s.get("delivers", "0/0"),
                qos_errors=s.get("qos_errors", 0),
                other_errors=s.get("other_errors", 0),
            ))

        connected = sum(1 for e in entries if e.sessions_count > 0)
        with_errors = sum(1 for e in entries if e.qos_errors > 0 or e.other_errors > 0)

        return SmppConnectorsHealthOut(
            connectors=entries,
            total=len(entries),
            connected=connected,
            with_errors=with_errors,
        )
