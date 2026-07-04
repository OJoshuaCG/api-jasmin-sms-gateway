from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_user_list,
    parse_user_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.logger import get_logger
from app.exceptions import AppHttpException
from app.schemas.users import UserCreate, UserOut, UserStatusUpdate, UserUpdate

logger = get_logger(__name__)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


def _ud(value) -> str:
    """Convert None to 'UD' (Unlimited/Default) for jcli."""
    return "UD" if value is None else str(value)


def _build_user_fields(data: UserCreate | UserUpdate) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []

    if isinstance(data, UserCreate):
        fields.append(("password", data.password))

    if isinstance(data, UserUpdate) and data.password is not None:
        fields.append(("password", data.password))

    if isinstance(data, UserUpdate) and data.gid is not None:
        fields.append(("gid", data.gid))

    if isinstance(data, UserUpdate) and data.username is not None:
        fields.append(("username", data.username))

    # MT Quota
    if data.mt_throughput is not None:
        fields.append(("mt_messaging_cred quota http_throughput", str(data.mt_throughput)))
    if getattr(data, "smpps_throughput", None) is not None:
        fields.append(("mt_messaging_cred quota smpps_throughput", _ud(data.smpps_throughput)))
    if data.balance is not None:
        fields.append(("mt_messaging_cred quota balance", _ud(data.balance)))
    if data.sms_count is not None:
        fields.append(("mt_messaging_cred quota sms_count", _ud(data.sms_count)))
    if getattr(data, "mt_quota_early_percent", None) is not None:
        fields.append(("mt_messaging_cred quota early_percent", _ud(data.mt_quota_early_percent)))

    # MT Auth — keys match exactly what jcli accepts (confirmed via user -s)
    for attr, jcli_key in [
        ("mt_auth_http_send", "http_send"),
        ("mt_auth_http_balance", "http_balance"),
        ("mt_auth_http_rate", "http_rate"),
        ("mt_auth_http_bulk", "http_bulk"),
        ("mt_auth_smpps_send", "smpps_send"),
        ("mt_auth_long_content", "http_long_content"),
        ("mt_auth_dlr_level", "dlr_level"),
        ("mt_auth_http_dlr_method", "http_dlr_method"),
        ("mt_auth_src_addr", "src_addr"),
        ("mt_auth_priority", "priority"),
        ("mt_auth_validity_period", "validity_period"),
        ("mt_auth_schedule_at", "schedule_delivery_time"),
        ("mt_auth_hex_content", "hex_content"),
    ]:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((f"mt_messaging_cred authorization {jcli_key}", str(val)))

    # MT Value Filters — jcli key is "valuefilter" (no underscore)
    for attr, jcli_key in [
        ("mt_filter_src_addr", "src_addr"),
        ("mt_filter_dst_addr", "dst_addr"),
        ("mt_filter_content", "content"),
        ("mt_filter_priority", "priority"),
        ("mt_filter_validity_period", "validity_period"),
    ]:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((f"mt_messaging_cred valuefilter {jcli_key}", str(val)))

    # MT Default values
    if getattr(data, "mt_default_src_addr", None) is not None:
        fields.append(("mt_messaging_cred defaultvalue src_addr", str(data.mt_default_src_addr)))

    # SMPP Server creds — keys confirmed via user -s output
    if getattr(data, "smpps_allow_bind", None) is not None:
        fields.append(("smpps_cred authorization bind", str(data.smpps_allow_bind)))
    if getattr(data, "smpps_max_bindings", None) is not None:
        fields.append(("smpps_cred quota max_bindings", _ud(data.smpps_max_bindings)))

    return fields


class UsersController:

    async def list_users(self) -> list[UserOut]:
        try:
            output = await _telnet().execute("user --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("user --list raw output: %r", output)
        rows = parse_user_list(output)
        enabled_map = {r["uid"]: r["enabled"] for r in rows}
        result = []
        for r in rows:
            try:
                show_out = await _telnet().execute(f"user -s {r['uid']}")
                if not show_out or "Error" in show_out or "Unknown" in show_out:
                    continue
                user = UserOut(**parse_user_show(show_out))
                user.enabled = enabled_map.get(r["uid"], True)
                result.append(user)
            except (TelnetNotConnectedError, AppHttpException):
                pass
        return result

    async def _get_enabled(self, uid: str) -> bool:
        """Fetch enabled state from user --list (user -s doesn't expose it)."""
        try:
            list_out = await _telnet().execute("user --list")
        except TelnetNotConnectedError:
            return True
        for row in parse_user_list(list_out):
            if row["uid"] == uid:
                return row["enabled"]
        return True

    async def get_user(self, uid: str) -> UserOut:
        try:
            output = await _telnet().execute(f"user -s {uid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"User '{uid}' not found", 404, {"uid": uid})
        user = UserOut(**parse_user_show(output))
        user.enabled = await self._get_enabled(uid)
        return user

    async def create_user(self, data: UserCreate) -> UserOut:
        fields = [("uid", data.uid), ("gid", data.gid), ("username", data.username)] + _build_user_fields(data)
        try:
            output = await _telnet().execute_interactive(
                "user --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"User '{data.uid}' already exists", 409, {"uid": data.uid, "gid": data.gid})
            raise AppHttpException(msg, 400, {"uid": data.uid, "gid": data.gid})
        return await self.get_user(data.uid)

    async def update_user(self, uid: str, data: UserUpdate) -> UserOut:
        await self.get_user(uid)  # 404 if not exists
        fields = _build_user_fields(data)
        if not fields:
            return await self.get_user(uid)
        try:
            output = await _telnet().execute_interactive(
                f"user -u {uid}",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"uid": uid})
        return await self.get_user(uid)

    async def delete_user(self, uid: str) -> None:
        await self.get_user(uid)
        try:
            output = await _telnet().execute(f"user -r {uid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"uid": uid})

    async def update_user_status(self, uid: str, data: UserStatusUpdate) -> UserOut:
        await self.get_user(uid)
        cmd = f"user -{'e' if data.enabled else 'd'} {uid}"
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"uid": uid, "enabled": data.enabled})
        return await self.get_user(uid)
