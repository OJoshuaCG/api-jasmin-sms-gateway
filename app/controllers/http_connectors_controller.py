from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_httpccm_list,
    parse_httpccm_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.logger import get_logger
from app.exceptions import AppHttpException
from app.schemas.http_connectors import HttpConnectorCreate, HttpConnectorOut, HttpConnectorUpdate

logger = get_logger(__name__)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


class HttpConnectorsController:

    async def list_connectors(self) -> list[HttpConnectorOut]:
        try:
            output = await _telnet().execute("httpccm --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("httpccm --list raw output: %r", output)
        rows = parse_httpccm_list(output)
        result = []
        for r in rows:
            try:
                result.append(await self.get_connector(r["cid"]))
            except AppHttpException:
                pass
        return result

    async def get_connector(self, cid: str) -> HttpConnectorOut:
        try:
            output = await _telnet().execute(f"httpccm -s {cid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"HTTP connector '{cid}' not found", 404, {"cid": cid})
        return HttpConnectorOut(**parse_httpccm_show(output))

    async def create_connector(self, data: HttpConnectorCreate) -> HttpConnectorOut:
        fields = [
            ("cid", data.cid),
            ("url", data.url),
            ("method", data.method),
        ]
        try:
            output = await _telnet().execute_interactive(
                "httpccm --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"HTTP connector '{data.cid}' already exists", 409, {"cid": data.cid})
            raise AppHttpException(msg, 400, {"cid": data.cid})
        return await self.get_connector(data.cid)

    async def update_connector(self, cid: str, data: HttpConnectorUpdate) -> HttpConnectorOut:
        # httpccm has no --update command; must delete and recreate
        existing = await self.get_connector(cid)
        url = data.url if data.url is not None else existing.url
        method = data.method if data.method is not None else existing.method
        await self.delete_connector(cid)
        create_data = HttpConnectorCreate(cid=cid, url=url, method=method)
        return await self.create_connector(create_data)

    async def delete_connector(self, cid: str) -> None:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"httpccm -r {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"cid": cid})
