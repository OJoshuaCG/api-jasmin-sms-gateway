from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_user_list,
    parse_user_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.users import UserCreate, UserOut, UserStatusUpdate, UserUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


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

    # Throughput
    if data.mt_throughput is not None:
        fields.append(("mt_messaging_cred quota http_throughput", str(data.mt_throughput)))
    if data.mo_throughput is not None:
        fields.append(("mo_messaging_cred quota mo_throughput", str(data.mo_throughput)))

    # Balance / Quota
    if data.balance is not None:
        fields.append(("mt_messaging_cred quota balance", _ud(data.balance)))
    if data.sms_count is not None:
        fields.append(("mt_messaging_cred quota sms_count", _ud(data.sms_count)))

    # MT Auth
    for attr, jcli_key in [
        ("mt_auth_priority", "priority"),
        ("mt_auth_validity_period", "validity_period"),
        ("mt_auth_src_addr", "src_addr"),
        ("mt_auth_schedule_at", "schedule_at"),
        ("mt_auth_dlr_level", "dlr_level"),
        ("mt_auth_long_content", "http_long_content"),
    ]:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((f"mt_messaging_cred authorization {jcli_key}", str(val)))

    # Value Filters
    for attr, jcli_key in [
        ("mt_filter_src_addr", "src_addr"),
        ("mt_filter_dst_addr", "dst_addr"),
        ("mt_filter_content", "content"),
    ]:
        val = getattr(data, attr, None)
        if val is not None:
            fields.append((f"mt_messaging_cred value_filter {jcli_key}", str(val)))

    # SMPP Server creds
    if getattr(data, "smpps_allow_bind", None) is not None:
        fields.append(("smpps_cred authorization bind", str(data.smpps_allow_bind)))
    if getattr(data, "smpps_max_bindings", None) is not None:
        fields.append(("smpps_cred quota max_bindings", _ud(data.smpps_max_bindings)))
    if getattr(data, "smpps_quota_sms_count", None) is not None:
        fields.append(("smpps_cred quota quota_sms_count", _ud(data.smpps_quota_sms_count)))
    if getattr(data, "smpps_throughput", None) is not None:
        fields.append(("smpps_cred quota throughput", _ud(data.smpps_throughput)))

    return fields


class UsersController:

    async def list_users(self) -> list[UserOut]:
        try:
            output = await _telnet().execute("user --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        rows = parse_user_list(output)
        result = []
        for r in rows:
            try:
                result.append(await self.get_user(r["uid"]))
            except AppHttpException:
                pass
        return result

    async def get_user(self, uid: str) -> UserOut:
        try:
            output = await _telnet().execute(f"user --show -u {uid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"User '{uid}' not found", 404)
        return UserOut(**parse_user_show(output))

    async def create_user(self, data: UserCreate) -> UserOut:
        fields = _build_user_fields(data)
        try:
            output = await _telnet().execute_interactive(
                f"user --add -u {data.uid} -g {data.gid}",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"User '{data.uid}' already exists", 409)
            raise AppHttpException(msg, 400)
        return await self.get_user(data.uid)

    async def update_user(self, uid: str, data: UserUpdate) -> UserOut:
        await self.get_user(uid)  # 404 if not exists
        fields = _build_user_fields(data)
        if not fields:
            return await self.get_user(uid)
        try:
            output = await _telnet().execute_interactive(
                f"user --update -u {uid}",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_user(uid)

    async def delete_user(self, uid: str) -> None:
        await self.get_user(uid)
        try:
            output = await _telnet().execute(f"user --remove -u {uid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)

    async def update_user_status(self, uid: str, data: UserStatusUpdate) -> UserOut:
        await self.get_user(uid)
        cmd = f"user --{'enable' if data.enabled else 'disable'} -u {uid}"
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_user(uid)
