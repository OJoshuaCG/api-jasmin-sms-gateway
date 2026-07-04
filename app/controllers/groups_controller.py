from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_group_list,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.groups import GroupCreate, GroupOut, GroupUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _handle_not_connected(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


class GroupsController:

    async def list_groups(self) -> list[GroupOut]:
        try:
            output = await _telnet().execute("group --list")
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        rows = parse_group_list(output)
        return [GroupOut(**r) for r in rows]

    async def get_group(self, gid: str) -> GroupOut:
        """Jasmin has no 'group --show' command; use --list to verify existence."""
        try:
            output = await _telnet().execute("group --list")
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        rows = parse_group_list(output)
        for row in rows:
            if row["gid"] == gid:
                return GroupOut(**row)
        raise AppHttpException(f"Group '{gid}' not found", 404, {"gid": gid})

    async def create_group(self, data: GroupCreate) -> GroupOut:
        try:
            existing = await self.get_group(data.gid)
            raise AppHttpException(
                f"Group '{data.gid}' already exists", 409,
                {"gid": data.gid, "existing": existing.model_dump(exclude_none=True)},
            )
        except AppHttpException as exc:
            if exc.status_code != 404:
                raise

        try:
            output = await _telnet().execute_interactive(
                "group --add",
                [("gid", data.gid)],
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"gid": data.gid})
        return await self.get_group(data.gid)

    async def update_group(self, gid: str, data: GroupUpdate) -> GroupOut:
        await self.get_group(gid)  # 404 if not exists
        cmd = f"group -{'e' if data.enabled else 'd'} {gid}"
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"gid": gid, "enabled": data.enabled})
        return await self.get_group(gid)

    async def delete_group(self, gid: str) -> None:
        await self.get_group(gid)  # 404 if not exists
        try:
            output = await _telnet().execute(f"group -r {gid}", persist=True)
        except TelnetNotConnectedError as exc:
            _handle_not_connected(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "users" in msg.lower():
                raise AppHttpException("Cannot remove group with assigned users", 409, {"gid": gid})
            raise AppHttpException(msg, 400, {"gid": gid})
