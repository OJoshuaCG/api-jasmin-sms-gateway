from app.core.jasmin_parsers import (
    parse_stats_httpapi,
    parse_stats_smppc,
    parse_stats_smppcs,
    parse_stats_smppsapi,
    parse_stats_user,
    parse_stats_users,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.stats import (
    GlobalStatsOut,
    HttpApiStatsOut,
    SmppConnectorStatsOut,
    SmppServerApiStatsOut,
    UserStatsOut,
)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


class StatsController:

    async def get_global_stats(self) -> GlobalStatsOut:
        try:
            smppcs_out = await _telnet().execute("stats --smppcs")
            users_out = await _telnet().execute("stats --users")
            httpapi_out = await _telnet().execute("stats --httpapi")
            smppsapi_out = await _telnet().execute("stats --smppsapi")
        except TelnetNotConnectedError as exc:
            _503(exc)
        return GlobalStatsOut(
            smpp_connectors=parse_stats_smppcs(smppcs_out),
            users=parse_stats_users(users_out),
            http_api=HttpApiStatsOut(**parse_stats_httpapi(httpapi_out)),
            smpp_server_api=SmppServerApiStatsOut(**parse_stats_smppsapi(smppsapi_out)),
        )

    async def get_smppccm_stats(self, cid: str) -> SmppConnectorStatsOut:
        try:
            output = await _telnet().execute(f"stats --smppc={cid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Unknown" in output or "Error" in output:
            raise AppHttpException(f"Stats for connector '{cid}' not found", 404, {"cid": cid})
        return SmppConnectorStatsOut(**parse_stats_smppc(output, cid))

    async def get_user_stats(self, uid: str) -> UserStatsOut:
        try:
            output = await _telnet().execute(f"stats --user={uid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Unknown" in output or "Error" in output:
            raise AppHttpException(f"Stats for user '{uid}' not found", 404, {"uid": uid})
        return UserStatsOut(**parse_stats_user(output, uid))

    async def get_httpapi_stats(self) -> HttpApiStatsOut:
        try:
            output = await _telnet().execute("stats --httpapi")
        except TelnetNotConnectedError as exc:
            _503(exc)
        return HttpApiStatsOut(**parse_stats_httpapi(output))

    async def get_smppsapi_stats(self) -> SmppServerApiStatsOut:
        try:
            output = await _telnet().execute("stats --smppsapi")
        except TelnetNotConnectedError as exc:
            _503(exc)
        return SmppServerApiStatsOut(**parse_stats_smppsapi(output))
