from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_filter_list,
    parse_filter_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.logger import get_logger
from app.exceptions import AppHttpException
from app.schemas.filters import FilterCreate, FilterOut, FilterUpdate

logger = get_logger(__name__)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


# Maps filter type → list of (param_key_in_schema, jcli_field_name) tuples
# jcli field names must match exactly what Jasmin jcli expects.
_FILTER_FIELDS: dict[str, list[tuple[str, str]]] = {
    "TransparentFilter": [],
    "ConnectorFilter": [("cid", "cid")],
    "UserFilter": [("uid", "uid")],
    "GroupFilter": [("gid", "gid")],
    "SourceAddrFilter": [("source_addr", "source_addr")],
    "DestinationAddrFilter": [("destination_addr", "destination_addr")],
    "ShortMessageFilter": [("short_message", "short_message")],
    "TagFilter": [("tag", "tag")],
    # dateInterval / timeInterval: format "START;END" passed as a single value
    "DateIntervalFilter": [("dateInterval", "dateInterval")],
    "TimeIntervalFilter": [("timeInterval", "timeInterval")],
    # pyCode: Python code string (not a file path)
    "EvalPyFilter": [("pyCode", "pyCode")],
}


def _build_filter_fields(data: FilterCreate | FilterUpdate, fid: str) -> list[tuple[str, str]]:
    """Build interactive fields for filter --add."""
    fields: list[tuple[str, str]] = [
        ("type", data.type),
        ("fid", fid),
    ]
    params = data.params or {}
    for param_key, jcli_key in _FILTER_FIELDS.get(data.type, []):
        # Accept both the canonical key and the jcli key from params
        val = params.get(param_key) or params.get(jcli_key)
        if val is not None:
            if isinstance(val, list):
                fields.append((jcli_key, ",".join(str(v) for v in val)))
            else:
                fields.append((jcli_key, str(val)))
    return fields


class FiltersController:

    async def list_filters(self) -> list[FilterOut]:
        try:
            output = await _telnet().execute("filter --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("filter --list raw output: %r", output)
        rows = parse_filter_list(output)
        return [FilterOut(**r) for r in rows]

    async def get_filter(self, fid: str) -> FilterOut:
        try:
            output = await _telnet().execute(f"filter -s {fid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Unknown" in output:
            raise AppHttpException(f"Filter '{fid}' not found", 404, {"fid": fid})
        parsed = parse_filter_show(output)
        parsed["fid"] = fid
        return FilterOut(**parsed)

    async def create_filter(self, data: FilterCreate) -> FilterOut:
        try:
            existing = await self.get_filter(data.fid)
            raise AppHttpException(
                f"Filter '{data.fid}' already exists", 409,
                {"fid": data.fid, "existing": existing.model_dump(exclude_none=True)},
            )
        except AppHttpException as exc:
            if exc.status_code != 404:
                raise

        fields = _build_filter_fields(data, data.fid)
        try:
            output = await _telnet().execute_interactive(
                "filter --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"fid": data.fid, "filter_type": data.type})
        return await self.get_filter(data.fid)

    async def update_filter(self, fid: str, data: FilterUpdate) -> FilterOut:
        # jcli has no filter --update; must delete + recreate
        existing = await self.get_filter(fid)
        try:
            del_out = await _telnet().execute(f"filter -r {fid}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(del_out):
            raise AppHttpException(
                f"Failed to remove filter for update: {extract_error_message(del_out)}", 400,
                {"fid": fid, "filter_type": data.type},
            )
        create_data = FilterCreate(fid=fid, type=data.type, params=data.params)
        fields = _build_filter_fields(create_data, fid)
        try:
            add_out = await _telnet().execute_interactive(
                "filter --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            # Attempt restore
            restore = FilterCreate(fid=fid, type=existing.type, params=existing.params)
            await _telnet().execute_interactive(
                "filter --add", _build_filter_fields(restore, fid), persist=True
            )
            _503(exc)
        if not is_success(add_out):
            # Attempt restore
            restore = FilterCreate(fid=fid, type=existing.type, params=existing.params)
            await _telnet().execute_interactive(
                "filter --add", _build_filter_fields(restore, fid), persist=True
            )
            raise AppHttpException(extract_error_message(add_out), 400, {"fid": fid, "filter_type": create_data.type})
        return await self.get_filter(fid)

    async def delete_filter(self, fid: str) -> None:
        await self.get_filter(fid)
        try:
            output = await _telnet().execute(f"filter -r {fid}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"fid": fid})
