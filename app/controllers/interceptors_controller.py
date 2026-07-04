from pathlib import Path

from app.core.environments import JASMIN_SCRIPTS_DIR
from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_interceptor_list,
    parse_interceptor_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.core.logger import get_logger
from app.exceptions import AppHttpException
from app.schemas.interceptors import (
    InterceptorOut,
    MoInterceptorCreate,
    MoInterceptorUpdate,
    MtInterceptorCreate,
    MtInterceptorUpdate,
)

logger = get_logger(__name__)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"error": str(exc)})


def _save_script(prefix: str, order: int, script: str) -> str:
    scripts_dir = Path(JASMIN_SCRIPTS_DIR)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    path = scripts_dir / f"{prefix}_{order}.py"
    path.write_text(script, encoding="utf-8")
    return str(path)


def _script_path(prefix: str, order: int) -> str:
    return str(Path(JASMIN_SCRIPTS_DIR) / f"{prefix}_{order}.py")


def _build_interceptor_fields(
    type_: str, order: int, script_path: str, filters: list[str]
) -> list[tuple[str, str]]:
    """Build interactive fields for mt/mointerceptor --add.

    The script field uses Jasmin's python3(/path) syntax.
    """
    fields: list[tuple[str, str]] = [
        ("type", type_),
        ("order", str(order)),
        ("script", f"python3({script_path})"),
    ]
    if filters:
        fields.append(("filters", ";".join(filters)))
    return fields


def _make_interceptor_out(kv: dict, prefix: str, order: int) -> InterceptorOut:
    return InterceptorOut(
        order=order,
        type=kv.get("type", ""),
        filters=[],  # filter FIDs are not recoverable from Jasmin show output
        script_path=_script_path(prefix, order),
    )


class MtInterceptorsController:

    async def list_interceptors(self) -> list[InterceptorOut]:
        try:
            output = await _telnet().execute("mtinterceptor --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("mtinterceptor --list raw output: %r", output)
        rows = parse_interceptor_list(output)
        result = []
        for r in rows:
            try:
                item = await self.get_interceptor(r["order"])
                result.append(item)
            except AppHttpException:
                pass
        return result

    async def get_interceptor(self, order: int) -> InterceptorOut:
        try:
            output = await _telnet().execute(f"mtinterceptor -s {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MT interceptor with order {order} not found", 404, {"order": order})
        kv = parse_interceptor_show(output)
        return _make_interceptor_out(kv, "mt", order)

    async def create_interceptor(self, data: MtInterceptorCreate) -> InterceptorOut:
        try:
            existing = await self.get_interceptor(data.order)
            raise AppHttpException(
                f"MT interceptor with order {data.order} already exists", 409,
                {"order": data.order, "existing": existing.model_dump(exclude_none=True)},
            )
        except AppHttpException as exc:
            if exc.status_code != 404:
                raise

        script_path = _save_script("mt", data.order, data.script)
        fields = _build_interceptor_fields(data.type, data.order, script_path, data.filters)
        try:
            output = await _telnet().execute_interactive(
                "mtinterceptor --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"order": data.order, "interceptor_type": data.type})
        return await self.get_interceptor(data.order)

    async def update_interceptor(self, order: int, data: MtInterceptorUpdate) -> InterceptorOut:
        existing = await self.get_interceptor(order)
        await self.delete_interceptor(order)
        if data.script is not None:
            script = data.script
        else:
            try:
                script = Path(existing.script_path).read_text(encoding="utf-8")
            except (FileNotFoundError, OSError):
                raise AppHttpException(
                    "Script file not found on disk; provide 'script' in the request body", 400,
                    {"order": order, "script_path": existing.script_path},
                )
        filters = data.filters if data.filters is not None else existing.filters
        create_data = MtInterceptorCreate(
            type=existing.type, order=order, filters=filters, script=script
        )
        return await self.create_interceptor(create_data)

    async def delete_interceptor(self, order: int) -> None:
        await self.get_interceptor(order)
        try:
            output = await _telnet().execute(f"mtinterceptor -r {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"order": order})

    async def flush_interceptors(self) -> None:
        try:
            output = await _telnet().execute("mtinterceptor --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"command": "mtinterceptor --flush"})


class MoInterceptorsController:

    async def list_interceptors(self) -> list[InterceptorOut]:
        try:
            output = await _telnet().execute("mointerceptor --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
        logger.debug("mointerceptor --list raw output: %r", output)
        rows = parse_interceptor_list(output)
        result = []
        for r in rows:
            try:
                item = await self.get_interceptor(r["order"])
                result.append(item)
            except AppHttpException:
                pass
        return result

    async def get_interceptor(self, order: int) -> InterceptorOut:
        try:
            output = await _telnet().execute(f"mointerceptor -s {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MO interceptor with order {order} not found", 404, {"order": order})
        kv = parse_interceptor_show(output)
        return _make_interceptor_out(kv, "mo", order)

    async def create_interceptor(self, data: MoInterceptorCreate) -> InterceptorOut:
        try:
            existing = await self.get_interceptor(data.order)
            raise AppHttpException(
                f"MO interceptor with order {data.order} already exists", 409,
                {"order": data.order, "existing": existing.model_dump(exclude_none=True)},
            )
        except AppHttpException as exc:
            if exc.status_code != 404:
                raise

        script_path = _save_script("mo", data.order, data.script)
        fields = _build_interceptor_fields(data.type, data.order, script_path, data.filters)
        try:
            output = await _telnet().execute_interactive(
                "mointerceptor --add",
                fields,
                persist=True,
            )
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"order": data.order, "interceptor_type": data.type})
        return await self.get_interceptor(data.order)

    async def update_interceptor(self, order: int, data: MoInterceptorUpdate) -> InterceptorOut:
        existing = await self.get_interceptor(order)
        await self.delete_interceptor(order)
        if data.script is not None:
            script = data.script
        else:
            try:
                script = Path(existing.script_path).read_text(encoding="utf-8")
            except (FileNotFoundError, OSError):
                raise AppHttpException(
                    "Script file not found on disk; provide 'script' in the request body", 400,
                    {"order": order, "script_path": existing.script_path},
                )
        filters = data.filters if data.filters is not None else existing.filters
        create_data = MoInterceptorCreate(
            type=existing.type, order=order, filters=filters, script=script
        )
        return await self.create_interceptor(create_data)

    async def delete_interceptor(self, order: int) -> None:
        await self.get_interceptor(order)
        try:
            output = await _telnet().execute(f"mointerceptor -r {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"order": order})

    async def flush_interceptors(self) -> None:
        try:
            output = await _telnet().execute("mointerceptor --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400, {"command": "mointerceptor --flush"})
