from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_route_list,
    parse_route_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.routes import MtRouteCreate, MtRouteOut, MtRouteUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


def _build_add_cmd(data: MtRouteCreate) -> str:
    connectors = ";".join(data.connectors)
    cmd = f"mtrouter --add -t {data.type} -r {data.order} -c {connectors}"
    if data.filters:
        cmd += f" -f {';'.join(data.filters)}"
    if data.rate is not None:
        cmd += f" -R {data.rate}"
    return cmd


def _parse_route_kv(kv: dict) -> MtRouteOut:
    connectors_raw = kv.get("connectors", kv.get("connector", ""))
    connectors = [c.strip() for c in str(connectors_raw).split(";") if c.strip()]
    filters_raw = kv.get("filters", kv.get("filter", ""))
    filters = [f.strip() for f in str(filters_raw).split(";") if f.strip()]
    return MtRouteOut(
        order=int(kv.get("order", 0)),
        type=kv.get("type", ""),
        connectors=connectors,
        filters=filters,
        rate=float(kv["rate"]) if kv.get("rate") not in (None, "", "None") else None,
    )


class MtRoutesController:

    async def list_routes(self) -> list[MtRouteOut]:
        try:
            output = await _telnet().execute("mtrouter --list")
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

    async def get_route(self, order: int) -> MtRouteOut:
        try:
            output = await _telnet().execute(f"mtrouter --show -r {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MT route with order {order} not found", 404)
        kv = parse_route_show(output)
        return _parse_route_kv(kv)

    async def create_route(self, data: MtRouteCreate) -> MtRouteOut:
        cmd = _build_add_cmd(data)
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"MT route with order {data.order} already exists", 409)
            raise AppHttpException(msg, 400)
        return await self.get_route(data.order)

    async def update_route(self, order: int, data: MtRouteUpdate) -> MtRouteOut:
        existing = await self.get_route(order)
        connectors = data.connectors if data.connectors is not None else existing.connectors
        filters = data.filters if data.filters is not None else existing.filters
        rate = data.rate if data.rate is not None else existing.rate

        # Delete + recreate
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
            output = await _telnet().execute(f"mtrouter --remove -r {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)

    async def flush_routes(self) -> None:
        try:
            output = await _telnet().execute("mtrouter --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
