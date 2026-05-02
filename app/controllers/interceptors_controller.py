from pathlib import Path

from app.core.environments import JASMIN_SCRIPTS_DIR
from app.core.jasmin_parsers import (
    extract_error_message,
    is_success,
    parse_interceptor_list,
    parse_interceptor_show,
)
from app.core.jasmin_telnet import JasminTelnetSession, TelnetNotConnectedError
from app.exceptions import AppHttpException
from app.schemas.interceptors import (
    InterceptorOut,
    MoInterceptorCreate,
    MoInterceptorUpdate,
    MtInterceptorCreate,
    MtInterceptorUpdate,
)


def _telnet() -> JasminTelnetSession:
    return JasminTelnetSession.get_instance()


def _503(exc: TelnetNotConnectedError) -> None:
    raise AppHttpException("Jasmin is not available", 503, {"detail": str(exc)})


def _save_script(prefix: str, order: int, script: str) -> str:
    scripts_dir = Path(JASMIN_SCRIPTS_DIR)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    path = scripts_dir / f"{prefix}_{order}.py"
    path.write_text(script, encoding="utf-8")
    return str(path)


def _parse_interceptor_kv(kv: dict, prefix: str = "mt") -> InterceptorOut:
    filters_raw = kv.get("filters", kv.get("filter", ""))
    filters = [f.strip() for f in str(filters_raw).split(";") if f.strip()]
    return InterceptorOut(
        order=int(kv.get("order", 0)),
        type=kv.get("type", ""),
        filters=filters,
        script_path=kv.get("script", ""),
    )


class MtInterceptorsController:

    async def list_interceptors(self) -> list[InterceptorOut]:
        try:
            output = await _telnet().execute("mtinterceptor --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
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
            output = await _telnet().execute(f"mtinterceptor --show -o {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MT interceptor with order {order} not found", 404)
        kv = parse_interceptor_show(output)
        return _parse_interceptor_kv(kv, "mt")

    async def create_interceptor(self, data: MtInterceptorCreate) -> InterceptorOut:
        script_path = _save_script("mt", data.order, data.script)
        cmd = f"mtinterceptor --add -t {data.type} -o {data.order} -s {script_path}"
        if data.filters:
            cmd += f" -f {';'.join(data.filters)}"
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"MT interceptor with order {data.order} already exists", 409)
            raise AppHttpException(msg, 400)
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
                    "Script file not found on disk; provide 'script' in the request body", 400
                )
        filters = data.filters if data.filters is not None else existing.filters
        create_data = MtInterceptorCreate(
            type=existing.type, order=order, filters=filters, script=script
        )
        return await self.create_interceptor(create_data)

    async def delete_interceptor(self, order: int) -> None:
        await self.get_interceptor(order)
        try:
            output = await _telnet().execute(f"mtinterceptor --remove -o {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)

    async def flush_interceptors(self) -> None:
        try:
            output = await _telnet().execute("mtinterceptor --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)


class MoInterceptorsController:

    async def list_interceptors(self) -> list[InterceptorOut]:
        try:
            output = await _telnet().execute("mointerceptor --list")
        except TelnetNotConnectedError as exc:
            _503(exc)
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
            output = await _telnet().execute(f"mointerceptor --show -o {order}")
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not output or "Error" in output or "Unknown" in output:
            raise AppHttpException(f"MO interceptor with order {order} not found", 404)
        kv = parse_interceptor_show(output)
        return _parse_interceptor_kv(kv, "mo")

    async def create_interceptor(self, data: MoInterceptorCreate) -> InterceptorOut:
        script_path = _save_script("mo", data.order, data.script)
        cmd = f"mointerceptor --add -t {data.type} -o {data.order} -s {script_path}"
        if data.filters:
            cmd += f" -f {';'.join(data.filters)}"
        try:
            output = await _telnet().execute(cmd, persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            msg = extract_error_message(output)
            if "already" in msg.lower():
                raise AppHttpException(f"MO interceptor with order {data.order} already exists", 409)
            raise AppHttpException(msg, 400)
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
                    "Script file not found on disk; provide 'script' in the request body", 400
                )
        filters = data.filters if data.filters is not None else existing.filters
        create_data = MoInterceptorCreate(
            type=existing.type, order=order, filters=filters, script=script
        )
        return await self.create_interceptor(create_data)

    async def delete_interceptor(self, order: int) -> None:
        await self.get_interceptor(order)
        try:
            output = await _telnet().execute(f"mointerceptor --remove -o {order}", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)

    async def flush_interceptors(self) -> None:
        try:
            output = await _telnet().execute("mointerceptor --flush", persist=True)
        except TelnetNotConnectedError as exc:
            _503(exc)
        if not is_success(output):
            raise AppHttpException(extract_error_message(output), 400)
