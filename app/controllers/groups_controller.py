from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_group_list,
    parse_group_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.groups import GroupCreate, GroupOut, GroupUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _handle_not_connected(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


class GroupsController:

    async def list_groups(self) -> list[GroupOut]:
        try:
            output = await _telnet().execute("group --list")
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        rows = parse_group_list(output)
        return [GroupOut(**r) for r in rows]

    async def get_group(self, gid: str) -> GroupOut:
        try:
            output = await _telnet().execute(f"group --show -g {gid}")
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"Group '{gid}' not found", 404)
        return GroupOut(**parse_group_show(output))

    async def create_group(self, data: GroupCreate) -> GroupOut:
        try:
            output = await _telnet().execute(f"group --add -g {data.gid}", persist=True)
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"Group '{data.gid}' already exists", 409)
            raise AppHttpException(msg, 400)
        return await self.get_group(data.gid)

    async def update_group(self, gid: str, data: GroupUpdate) -> GroupOut:
        await self.get_group(gid)  # 404 if not exists
        cmd = f"group --{'enable' if data.enabled else 'disable'} -g {gid}"
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
        return await self.get_group(gid)

    async def delete_group(self, gid: str) -> None:
        await self.get_group(gid)  # 404 if not exists
        try:
            output = await _telnet().execute(f"group --remove -g {gid}", persist=True)
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "users" in msg.lower():
                raise AppHttpException("Cannot remove group with assigned users", 409)
            raise AppHttpException(msg, 400)
