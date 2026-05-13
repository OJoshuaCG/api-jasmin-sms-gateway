from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_filter_list,
    parse_mt_route_show,
    parse_route_list,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.logger import get_logger
from app.exceptions import AppHttpException
from app.schemas.routes import MtRouteCreate, MtRouteOut, MtRouteUpdate

logger = get_logger(__name__)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


# Route types that require at least one filter field in jcli --add
_FILTER_REQUIRED_TYPES = ("StaticMTRoute", "FilteredMTRoute")


def _build_create_fields(
    data: MtRouteCreate, fallback_filter_fid: str = ""
) -> list[tuple[str, str]]:
    """Build interactive fields for mtrouter --add.

    Connector IDs must include the prefix (e.g. 'smppc(id)' or 'httpc(id)').
    For routes with a single connector, use 'connector'; for multi-connector
    route types use 'connectors' with semicolon-separated values.
    fallback_filter_fid is used when data.filters is empty but the route type
    requires at least one filter (e.g. StaticMTRoute).
    """
    fields: list[tuple[str, str]] = [
        ("type", data.type),
        ("order", str(data.order)),
    ]
    if data.type in ("RandomRoundrobinMTRoute", "FailoverMTRoute"):
        fields.append(("connectors", ";".join(data.connectors)))
    else:
        fields.append(("connector", data.connectors[0] if data.connectors else ""))

    effective_filters = data.filters or []
    if not effective_filters and data.type in _FILTER_REQUIRED_TYPES and fallback_filter_fid:
        effective_filters = [fallback_filter_fid]
    if effective_filters:
        fields.append(("filters", ";".join(effective_filters)))

    rate = data.rate if data.rate is not None else 0.0
    fields.append(("rate", str(rate)))
    return fields


class MtRoutesController:

    async def _resolve_transparent_filter_fid(self) -> str:
        """Return the FID of any TransparentFilter in Jasmin's filter list.

        Used as fallback when a route type requires filters but none are provided.
        Returns empty string if no TransparentFilter exists.
        """
        try:
            output = await _telnet().execute("filter --list")
        except TelnetNotConnectedError:
            return ""
        for row in parse_filter_list(output):
            if row.get("type") == "TransparentFilter":
                return row["fid"]
        return ""

    async def _get_route_filter_raw(self, order: int) -> str:
        """Parse mtrouter --list to find the filter indicator for a given order."""
        try:
            output = await _telnet().execute("mtrouter --list")
        except TelnetNotConnectedError:
            return ""
        for row in parse_route_list(output):
            if row["order"] == order:
                return row.get("filter_raw", "")
        return ""

    async def list_routes(self) -> list[MtRouteOut]:
        try:
            output = await _telnet().execute("mtrouter --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("mtrouter --list raw output: %r", output)
        rows = parse_route_list(output)
        result = []
        for r in rows:
            try:
                route = await self.get_route(r["order"])
                result.append(route)
            except AppHttpException:
                pass
        return result

    async def get_route(self, order: int) -> MtRouteOut:
        try:
            output = await _telnet().execute(f"mtrouter -s {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MT route with order {order} not found", 404, {"order": order})
        data = parse_mt_route_show(output, order)
        return MtRouteOut(**data)

    async def create_route(self, data: MtRouteCreate) -> MtRouteOut:
        fallback_fid = ""
        if not data.filters and data.type in _FILTER_REQUIRED_TYPES:
            fallback_fid = await self._resolve_transparent_filter_fid()
            if not fallback_fid:
                raise AppHttpException(
                    f"{data.type} requires at least one filter; "
                    "provide 'filters' or create a TransparentFilter first",
                    400,
                    {"route_type": data.type, "order": data.order},
                )
        fields = _build_create_fields(data, fallback_filter_fid=fallback_fid)
        try:
            output = await _telnet().execute_interactive(
                "mtrouter --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"MT route with order {data.order} already exists", 409, {"order": data.order, "route_type": data.type})
            raise AppHttpException(msg, 400, {"order": data.order, "route_type": data.type})
        # DefaultRoute is always created at order 0 regardless of what was requested
        actual_order = 0 if data.type == "DefaultRoute" else data.order
        return await self.get_route(actual_order)

    async def update_route(self, order: int, data: MtRouteUpdate) -> MtRouteOut:
        existing = await self.get_route(order)
        connectors = data.connectors if data.connectors is not None else existing.connectors
        rate = data.rate if data.rate is not None else existing.rate

        # Resolve filters: use provided filters, or auto-detect from current route
        if data.filters is not None:
            filters = data.filters
        else:
            # Filter FIDs are not in route show output — check list for TransparentFilter indicator
            filter_raw = await self._get_route_filter_raw(order)
            if filter_raw == "<T>" or not filter_raw:
                # TransparentFilter or no filter (DefaultRoute) — auto-resolve
                filters = []
            else:
                raise AppHttpException(
                    "Cannot update this route without providing 'filters'; "
                    "filter FIDs cannot be recovered from Jasmin",
                    400,
                    {"order": order, "route_type": existing.type, "filter_raw": filter_raw},
                )

        await self.delete_route(order)
        create_data = MtRouteCreate(
            type=existing.type,
            order=order,
            connectors=connectors,
            filters=filters,
            rate=rate,
        )
        return await self.create_route(create_data)

    async def delete_route(self, order: int) -> None:
        await self.get_route(order)
        try:
            output = await _telnet().execute(f"mtrouter -r {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"order": order})

    async def flush_routes(self) -> None:
        try:
            output = await _telnet().execute("mtrouter --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"command": "mtrouter --flush"})
