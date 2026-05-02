from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_smppserver_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.smpp_server import SmppServerOut, SmppServerUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


class SmppServerController:

    async def get_config(self) -> SmppServerOut:
        try:
            output = await _telnet().execute("smppserver --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output:
            raise AppHttpException("Failed to retrieve SMPP server config", 500)
        return SmppServerOut(**parse_smppserver_show(output))

    async def update_config(self, data: SmppServerUpdate) -> SmppServerOut:
        fields: list[tuple[str, str]] = []
        if data.host is not None:
            fields.append(("host", data.host))
        if data.port is not None:
            fields.append(("port", str(data.port)))
        if data.max_bindings is not None:
            fields.append(("max_bindings", str(data.max_bindings)))
        if not fields:
            return await self.get_config()
        try:
            output = await _telnet().execute_interactive(
                "smppserver --update", fields, persist=True
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_config()
