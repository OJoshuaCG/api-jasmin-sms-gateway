from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_route_list,
    parse_route_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.routes import MoRouteCreate, MoRouteOut, MoRouteUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


def _build_add_cmd(data: MoRouteCreate) -> str:
    cmd = f"morouter --add -t {data.type} -r {data.order} -c {data.connector}"
    if data.filters:
        cmd += f" -f {';'.join(data.filters)}"
    return cmd


def _parse_route_kv(kv: dict) -> MoRouteOut:
    connector = kv.get("connector", kv.get("connectors", ""))
    filters_raw = kv.get("filters", kv.get("filter", ""))
    filters = [f.strip() for f in str(filters_raw).split(";") if f.strip()]
    return MoRouteOut(
        order=int(kv.get("order", 0)),
        type=kv.get("type", ""),
        connector=str(connector),
        filters=filters,
    )


class MoRoutesController:

    async def list_routes(self) -> list[MoRouteOut]:
        try:
            output = await _telnet().execute("morouter --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
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
            output = await _telnet().execute(f"morouter --show -r {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MO route with order {order} not found", 404)
        kv = parse_route_show(output)
        return _parse_route_kv(kv)

    async def create_route(self, data: MoRouteCreate) -> MoRouteOut:
        cmd = _build_add_cmd(data)
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"MO route with order {data.order} already exists", 409)
            raise AppHttpException(msg, 400)
        return await self.get_route(data.order)

    async def update_route(self, order: int, data: MoRouteUpdate) -> MoRouteOut:
        existing = await self.get_route(order)
        connector = data.connector if data.connector is not None else existing.connector
        filters = data.filters if data.filters is not None else existing.filters
        await self.delete_route(order)
        create_data = MoRouteCreate(
            type=existing.type, order=order, connector=connector, filters=filters
        )
        return await self.create_route(create_data)

    async def delete_route(self, order: int) -> None:
        await self.get_route(order)
        try:
            output = await _telnet().execute(f"morouter --remove -r {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)

    async def flush_routes(self) -> None:
        try:
            output = await _telnet().execute("morouter --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
