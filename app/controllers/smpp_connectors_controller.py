from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_smppccm_list,
    parse_smppccm_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.logger import get_logger
from app.exceptions import AppHttpException
from app.schemas.smpp_connectors import (
    SmppConnectorCreate,
    SmppConnectorOut,
    SmppConnectorStatusOut,
    SmppConnectorUpdate,
)

logger = get_logger(__name__)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


def _bool_to_yn(value: bool) -> str:
    return "yes" if value else "no"


def _connector_fields(data: SmppConnectorCreate | SmppConnectorUpdate) -> list[tuple[str, str]]:
    """Map API schema fields to jcli interactive field names."""
    fields: list[tuple[str, str]] = []

    # Plain value fields
    simple: list[tuple[str, str]] = [
        ("host", "host"),
        ("port", "port"),
        ("username", "username"),
        ("password", "password"),
        ("submit_throughput", "submit_throughput"),
        ("dlr_expiry", "dlr_expiry"),
    ]
    for attr, jcli_key in simple:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((jcli_key, str(val)))

    # bind_to in schema → "bind" in jcli (bind type: transceiver/transmitter/receiver)
    if getattr(data, "bind_to", None) is not None:
        fields.append(("bind", str(data.bind_to)))

    # system_type → systype
    if getattr(data, "system_type", None) is not None:
        fields.append(("systype", str(data.system_type)))

    # address_range → addr_range
    if getattr(data, "address_range", None) is not None:
        fields.append(("addr_range", str(data.address_range)))

    # TON/NPI fields
    ton_npi: list[tuple[str, str]] = [
        ("source_addr_ton", "src_ton"),
        ("source_addr_npi", "src_npi"),
        ("dest_addr_ton", "dst_ton"),
        ("dest_addr_npi", "dst_npi"),
    ]
    for attr, jcli_key in ton_npi:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((jcli_key, str(val)))

    # Boolean reconnect fields use yes/no in jcli
    if getattr(data, "reconnect_on_connection_loss", None) is not None:
        fields.append(("con_loss_retry", _bool_to_yn(data.reconnect_on_connection_loss)))
    if getattr(data, "reconnect_on_connection_loss_delay", None) is not None:
        fields.append(("con_loss_delay", str(data.reconnect_on_connection_loss_delay)))
    if getattr(data, "reconnect_on_connection_failure", None) is not None:
        fields.append(("con_fail_retry", _bool_to_yn(data.reconnect_on_connection_failure)))
    if getattr(data, "reconnect_on_connection_failure_delay", None) is not None:
        fields.append(("con_fail_delay", str(data.reconnect_on_connection_failure_delay)))

    # bind_timeout → jcli "bind_to" (integer, seconds) — distinct from bind type
    if getattr(data, "bind_timeout", None) is not None:
        fields.append(("bind_to", str(data.bind_timeout)))

    # Timeouts
    for attr, jcli_key in [
        ("elink_interval", "elink_interval"),
        ("res_to", "res_to"),
        ("pdu_red_to", "pdu_red_to"),
        ("trx_to", "trx_to"),
        ("requeue_delay", "requeue_delay"),
    ]:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((jcli_key, str(val)))

    # Encoding / DLR
    for attr, jcli_key in [
        ("coding", "coding"),
        ("dlr_msgid", "dlr_msgid"),
    ]:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((jcli_key, str(val)))

    # TLS — yes/no
    if getattr(data, "ssl", None) is not None:
        fields.append(("ssl", _bool_to_yn(data.ssl)))

    return fields


class SmppConnectorsController:

    async def list_connectors(self) -> list[SmppConnectorOut]:
        try:
            output = await _telnet().execute("smppccm --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("smppccm --list raw output: %r", output)
        rows = parse_smppccm_list(output)
        result = []
        for r in rows:
            try:
                result.append(await self.get_connector(r["cid"]))
            except AppHttpException:
                pass
        return result

    async def get_connector(self, cid: str) -> SmppConnectorOut:
        try:
            output = await _telnet().execute(f"smppccm -s {cid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"SMPP connector '{cid}' not found", 404, {"cid": cid})
        return SmppConnectorOut(**parse_smppccm_show(output))

    async def create_connector(self, data: SmppConnectorCreate) -> SmppConnectorOut:
        try:
            existing = await self.get_connector(data.cid)
            raise AppHttpException(
                f"Connector '{data.cid}' already exists", 409,
                {"cid": data.cid, "existing": existing.model_dump(exclude_none=True)},
            )
        except AppHttpException as exc:
            if exc.status_code != 404:
                raise

        fields = [("cid", data.cid)] + _connector_fields(data)
        try:
            output = await _telnet().execute_interactive(
                "smppccm --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"cid": data.cid})
        return await self.get_connector(data.cid)

    async def update_connector(self, cid: str, data: SmppConnectorUpdate) -> SmppConnectorOut:
        await self.get_connector(cid)
        fields = _connector_fields(data)
        if not fields:
            return await self.get_connector(cid)
        try:
            output = await _telnet().execute_interactive(
                f"smppccm -u {cid}",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"cid": cid})
        return await self.get_connector(cid)

    async def delete_connector(self, cid: str) -> None:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"smppccm -r {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"cid": cid})

    async def start_connector(self, cid: str) -> SmppConnectorStatusOut:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"smppccm -1 {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"cid": cid})
        return await self.get_connector_status(cid)

    async def stop_connector(self, cid: str) -> SmppConnectorStatusOut:
        await self.get_connector(cid)
        try:
            output = await _telnet().execute(f"smppccm -0 {cid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"cid": cid})
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
        raise AppHttpException(f"SMPP connector '{cid}' not found", 404, {"cid": cid})
