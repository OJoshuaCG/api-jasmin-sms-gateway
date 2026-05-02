from app.core.jasmin_parsers import parse_stats_smppccm, parse_stats_user
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.stats import SmppConnectorStatsOut, UserStatsOut


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


class StatsController:

    async def get_global_stats(self) -> dict:
        try:
            output = await _telnet().execute("stats --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        return {"raw": output}

    async def get_smppccm_stats(self, cid: str) -> SmppConnectorStatsOut:
        try:
            output = await _telnet().execute(f"stats --smppccm -c {cid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output:
            raise AppHttpException(f"Stats for connector '{cid}' not found", 404)
        return SmppConnectorStatsOut(**parse_stats_smppccm(output, cid))

    async def get_user_stats(self, uid: str) -> UserStatsOut:
        try:
            output = await _telnet().execute(f"stats --user -u {uid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output:
            raise AppHttpException(f"Stats for user '{uid}' not found", 404)
        return UserStatsOut(**parse_stats_user(output, uid))
