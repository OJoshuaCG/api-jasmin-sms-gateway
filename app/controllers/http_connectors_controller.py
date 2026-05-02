from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_httpccm_list,
    parse_httpccm_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.http_connectors import HttpConnectorCreate, HttpConnectorOut, HttpConnectorUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


class HttpConnectorsController:

    async def list_connectors(self) -> list[HttpConnectorOut]:
        try:
            output = await _telnet().execute("httpccm --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        rows = parse_httpccm_list(output)
        return [HttpConnectorOut(**r) for r in rows]

    async def get_connector(self, cid: str) -> HttpConnectorOut:
        try:
            output = await _telnet().execute(f"httpccm --show -c {cid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"HTTP connector '{cid}' not found", 404)
        return HttpConnectorOut(**parse_httpccm_show(output))

    async def create_connector(self, data: HttpConnectorCreate) -> HttpConnectorOut:
        try:
            output = await _telnet().execute(
                f"httpccm --add -c {data.cid} -u {data.url} -m {data.method}",
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"HTTP connector '{data.cid}' already exists", 409)
            raise AppHttpException(msg, 400)
        return await self.get_connector(data.cid)

    async def update_connector(self, cid: str, data: HttpConnectorUpdate) -> HttpConnectorOut:
        await self.get_connector(cid)
        fields: list[tuple[str, str]] = []
        if data.url is not None:
            fields.append(("url", data.url))
        if data.method is not None:
            fields.append(("method", data.method))
        if not fields:
            return await self.get_connector(cid)
        try:
            output = await _telnet().execute_interactive(
                f"httpccm --update -c {cid}", fields, persist=True
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_connector(cid)

    async def delete_connector(self, cid: str) -> None:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"httpccm --remove -c {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
