from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_filter_list,
    parse_mo_route_show,
    parse_route_list,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.logger import get_logger
from app.exceptions import AppHttpException
from app.schemas.routes import MO_MULTI_CONNECTOR_TYPES, MoRouteCreate, MoRouteOut, MoRouteUpdate

logger = get_logger(__name__)

_FILTER_REQUIRED_TYPES = ("StaticMORoute", "RandomRoundrobinMORoute", "FailoverMORoute")


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


def _build_create_fields(
    data: MoRouteCreate, fallback_filter_fid: str = ""
) -> list[tuple[str, str]]:
    """Build interactive fields for morouter --add.

    Connector ID syntax: http(<cid>) for HTTP connectors, smpps(<cid>) for SMPP server.
    Multi-connector types (RandomRoundrobinMORoute, FailoverMORoute) use 'connectors'
    (plural, semicolon-separated). Single-connector types use 'connector'.
    """
    fields: list[tuple[str, str]] = [
        ("type", data.type),
        ("order", str(data.order)),
    ]
    if data.type in MO_MULTI_CONNECTOR_TYPES:
        fields.append(("connectors", ";".join(data.connectors or [])))
    else:
        fields.append(("connector", data.connector or ""))

    effective_filters = data.filters or []
    if not effective_filters and data.type in _FILTER_REQUIRED_TYPES and fallback_filter_fid:
        effective_filters = [fallback_filter_fid]
    if effective_filters:
        fields.append(("filters", ";".join(effective_filters)))
    return fields


class MoRoutesController:

    async def _resolve_transparent_filter_fid(self) -> str:
        try:
            output = await _telnet().execute("filter --list")
        except TelnetNotConnectedError:
            return ""
        for row in parse_filter_list(output):
            if row.get("type") == "TransparentFilter":
                return row["fid"]
        return ""

    async def _get_route_filter_raw(self, order: int) -> str:
        try:
            output = await _telnet().execute("morouter --list")
        except TelnetNotConnectedError:
            return ""
        for row in parse_route_list(output):
            if row["order"] == order:
                return row.get("filter_raw", "")
        return ""

    async def list_routes(self) -> list[MoRouteOut]:
        try:
            output = await _telnet().execute("morouter --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("morouter --list raw output: %r", output)
        rows = parse_route_list(output)
        result = []
        for r in rows:
            try:
                route = await self.get_route(r["order"])
                result.append(route)
            except AppHttpException:
                pass
        return result

    async def get_route(self, order: int) -> MoRouteOut:
        try:
            output = await _telnet().execute(f"morouter -s {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MO route with order {order} not found", 404, {"order": order})
        data = parse_mo_route_show(output, order)
        return MoRouteOut(**data)

    async def create_route(self, data: MoRouteCreate) -> MoRouteOut:
        check_order = 0 if data.type == "DefaultRoute" else data.order
        try:
            existing = await self.get_route(check_order)
            raise AppHttpException(
                f"MO route with order {check_order} already exists", 409,
                {"order": check_order, "existing": existing.model_dump(exclude_none=True)},
            )
        except AppHttpException as exc:
            if exc.status_code != 404:
                raise

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
                "morouter --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"order": data.order, "route_type": data.type})
        return await self.get_route(check_order)

    async def update_route(self, order: int, data: MoRouteUpdate) -> MoRouteOut:
        existing = await self.get_route(order)
        if existing.type in MO_MULTI_CONNECTOR_TYPES:
            connector = None
            connectors = data.connectors if data.connectors is not None else existing.connectors
        else:
            connector = data.connector if data.connector is not None else existing.connector
            connectors = None

        if data.filters is not None:
            filters = data.filters
        else:
            filter_raw = await self._get_route_filter_raw(order)
            if filter_raw == "<T>" or not filter_raw:
                filters = []
            else:
                raise AppHttpException(
                    "Cannot update this route without providing 'filters'; "
                    "filter FIDs cannot be recovered from Jasmin",
                    400,
                    {"order": order, "route_type": existing.type, "filter_raw": filter_raw},
                )

        await self.delete_route(order)
        create_data = MoRouteCreate(
            type=existing.type, order=order,
            connector=connector, connectors=connectors,
            filters=filters,
        )
        return await self.create_route(create_data)

    async def delete_route(self, order: int) -> None:
        await self.get_route(order)
        try:
            output = await _telnet().execute(f"morouter -r {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"order": order})

    async def flush_routes(self) -> None:
        try:
            output = await _telnet().execute("morouter --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"command": "morouter --flush"})
