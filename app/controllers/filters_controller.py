from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_filter_list,
    parse_filter_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.filters import FilterCreate, FilterOut, FilterUpdate


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


# Maps filter type → CLI flag for its main parameter
_FILTER_PARAM_FLAGS: dict[str, str] = {
    "ConnectorFilter": "-c",
    "UserFilter": "-u",
    "GroupFilter": "-g",
    "SrcAddrFilter": "-r",
    "DstAddrFilter": "-r",
    "ShortMessageFilter": "-r",
    "TagFilter": "-t",
}


def _build_filter_add_cmd(data: FilterCreate | FilterUpdate, fid: str) -> str:
    cmd = f"filter --add -f {fid} -t {data.type}"
    params = data.params or {}

    flag = _FILTER_PARAM_FLAGS.get(data.type)
    if flag:
        main_param = params.get("regex") or params.get("connector") or params.get(
            "uid") or params.get("gid") or params.get("tag")
        if main_param:
            cmd += f" {flag} {main_param}"

    elif data.type == "DateIntervalFilter":
        if "before_date" in params:
            cmd += f" --before {params['before_date']}"
        if "after_date" in params:
            cmd += f" --after {params['after_date']}"

    elif data.type == "TimeIntervalFilter":
        if "before_time" in params:
            cmd += f" --before {params['before_time']}"
        if "after_time" in params:
            cmd += f" --after {params['after_time']}"

    elif data.type == "DayFilter":
        days = params.get("days", [])
        if days:
            cmd += f" --days {','.join(str(d) for d in days)}"

    elif data.type == "EvalPyFilter":
        py_file = params.get("py_file") or params.get("script_path")
        if py_file:
            cmd += f" -y {py_file}"

    return cmd


class FiltersController:

    async def list_filters(self) -> list[FilterOut]:
        try:
            output = await _telnet().execute("filter --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        rows = parse_filter_list(output)
        return [FilterOut(**r) for r in rows]

    async def get_filter(self, fid: str) -> FilterOut:
        try:
            output = await _telnet().execute(f"filter --show -f {fid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"Filter '{fid}' not found", 404)
        return FilterOut(**parse_filter_show(output))

    async def create_filter(self, data: FilterCreate) -> FilterOut:
        cmd = _build_filter_add_cmd(data, data.fid)
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"Filter '{data.fid}' already exists", 409)
            raise AppHttpException(msg, 400)
        return await self.get_filter(data.fid)

    async def update_filter(self, fid: str, data: FilterUpdate) -> FilterOut:
        # jcli has no filter --update; must delete + recreate
        existing = await self.get_filter(fid)
        # Remove
        try:
            del_out = await _telnet().execute(f"filter --remove -f {fid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(del_out):
            raise AppHttpException(f"Failed to remove filter for update: {extract_error_message(del_out)}", 400)
        # Recreate
        create_data = FilterCreate(fid=fid, type=data.type, params=data.params)
        cmd = _build_filter_add_cmd(create_data, fid)
        try:
            add_out = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            # Attempt restore
            restore_cmd = _build_filter_add_cmd(
                FilterCreate(fid=fid, type=existing.type, params=existing.params), fid
            )
            await _telnet().execute(restore_cmd, persist=True)
            _503(exc)
        if not is_success(add_out):
            # Attempt restore
            restore_cmd = _build_filter_add_cmd(
                FilterCreate(fid=fid, type=existing.type, params=existing.params), fid
            )
            await _telnet().execute(restore_cmd, persist=True)
            raise AppHttpException(extract_error_message(add_out), 400)
        return await self.get_filter(fid)

    async def delete_filter(self, fid: str) -> None:
        await self.get_filter(fid)
        try:
            output = await _telnet().execute(f"filter --remove -f {fid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
