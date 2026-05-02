from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_smppccm_list,
    parse_smppccm_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.smpp_connectors import (
    SmppConnectorCreate,
    SmppConnectorOut,
    SmppConnectorStatusOut,
    SmppConnectorUpdate,
)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


def _connector_fields(data: SmppConnectorCreate | SmppConnectorUpdate) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    mapping = {
        "host": "host",
        "port": "port",
        "username": "username",
        "password": "password",
        "bind_to": "bind_to",
        "system_type": "system_type",
        "interface_version": "interface_version",
        "address_range": "address_range",
        "source_addr_ton": "source_addr_ton",
        "source_addr_npi": "source_addr_npi",
        "dest_addr_ton": "dest_addr_ton",
        "dest_addr_npi": "dest_addr_npi",
        "submit_throughput": "submit_throughput",
        "dlr_expiry": "dlr_expiry",
        "reconnect_on_connection_loss": "reconnect_on_connection_loss",
        "reconnect_on_connection_loss_delay": "reconnect_on_connection_loss_delay",
        "reconnect_on_connection_failure": "reconnect_on_connection_failure",
        "reconnect_on_connection_failure_delay": "reconnect_on_connection_failure_delay",
    }
    for attr, jcli_key in mapping.items():
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((jcli_key, str(val)))
    return fields


class SmppConnectorsController:

    async def list_connectors(self) -> list[SmppConnectorOut]:
        try:
            output = await _telnet().execute("smppccm --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        rows = parse_smppccm_list(output)
        # For list, we only have cid + status; return minimal objects
        result = []
        for r in rows:
            try:
                show_out = await self.get_connector(r["cid"])
                result.append(show_out)
            except AppHttpException:
                pass
        return result

    async def get_connector(self, cid: str) -> SmppConnectorOut:
        try:
            output = await _telnet().execute(f"smppccm --show -c {cid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"SMPP connector '{cid}' not found", 404)
        return SmppConnectorOut(**parse_smppccm_show(output))

    async def create_connector(self, data: SmppConnectorCreate) -> SmppConnectorOut:
        fields = _connector_fields(data)
        try:
            output = await _telnet().execute_interactive(
                f"smppccm --add -c {data.cid}",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"Connector '{data.cid}' already exists", 409)
            raise AppHttpException(msg, 400)
        return await self.get_connector(data.cid)

    async def update_connector(self, cid: str, data: SmppConnectorUpdate) -> SmppConnectorOut:
        await self.get_connector(cid)
        fields = _connector_fields(data)
        if not fields:
            return await self.get_connector(cid)
        try:
            output = await _telnet().execute_interactive(
                f"smppccm --update -c {cid}",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_connector(cid)

    async def delete_connector(self, cid: str) -> None:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"smppccm --remove -c {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)

    async def start_connector(self, cid: str) -> SmppConnectorStatusOut:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"smppccm --start -c {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_connector_status(cid)

    async def stop_connector(self, cid: str) -> SmppConnectorStatusOut:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"smppccm --stop -c {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_connector_status(cid)

    async def get_connector_status(self, cid: str) -> SmppConnectorStatusOut:
        try:
            output = await _telnet().execute("smppccm --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        rows = parse_smppccm_list(output)
        for r in rows:
            if r["cid"] == cid:
                return SmppConnectorStatusOut(
                    cid=cid,
                    status=r["status"],
                    sessions_count=r.get("sessions_count", 0),
                )
        raise AppHttpException(f"SMPP connector '{cid}' not found", 404)
