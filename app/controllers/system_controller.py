import httpx

from app.core.jasmin_http import get_jasmin_http_client
from app.core.jasmin_parsers import extract_error_message, is_success
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.system import HealthOut, JasminHttpStatus, SessionOut, TelnetStatus


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


class SystemController:

    async def health(self) -> HealthOut:
        telnet = _telnet()
        telnet_status = TelnetStatus(
            connected=telnet.is_connected,
            uptime_seconds=telnet.uptime_seconds,
            reconnecting=telnet.is_reconnecting,
        )
        # Probe Jasmin HTTP API
        http_reachable = False
        try:
            client = get_jasmin_http_client()
            resp = await client.get("/")
            http_reachable = resp.status_code < 500
        except Exception:
            http_reachable = False

        if telnet.is_connected and http_reachable:
            status = "ok"
        elif telnet.is_connected or http_reachable:
            status = "degraded"
        else:
            status = "error"

        return HealthOut(
            status=status,
            telnet=telnet_status,
            jasmin_http=JasminHttpStatus(reachable=http_reachable),
        )

    async def persist(self) -> str:
        try:
            return await _telnet().persist()
        except TelnetNotConnectedError as exc:
            raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})

    async def reload(self) -> str:
        try:
            output = await _telnet().execute("load")
        except TelnetNotConnectedError as exc:
            raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})
        if not is_success(output) and "loading" not in output.lower():
            raise AppHttpException(extract_error_message(output), 400)
        return "Configuration reloaded from disk"

    async def reconnect(self) -> str:
        try:
            await _telnet().force_reconnect()
            return "Reconnected successfully"
        except Exception as exc:
            raise AppHttpException(f"Reconnect failed: {exc}", 503)

    async def session_info(self) -> SessionOut:
        info = await _telnet().session_info()
        return SessionOut(**info)
