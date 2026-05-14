import json as _json

import httpx

from app.core.jasmin_http import get_jasmin_http_client
from app.exceptions import AppHttpException
from app.schemas.sms import SmsBinaryRequest, SmsBalanceOut, SmsRateOut, SmsSendOut, SmsSendRequest


def _http_client() -> httpx.AsyncClient:
    return get_jasmin_http_client()


class SmsController:

    async def send(self, data: SmsSendRequest) -> SmsSendOut:
        params: dict = {
            "username": data.username,
            "password": data.password,
            "to": data.to,
            "content": data.content,
            "coding": data.coding,
            "dlr": data.dlr,
        }
        if data.sender:
            params["from"] = data.sender
        if data.dlr_url:
            params["dlr-url"] = data.dlr_url
        if data.dlr_level is not None:
            params["dlr-level"] = data.dlr_level
        if data.dlr_method:
            params["dlr-method"] = data.dlr_method
        if data.priority is not None:
            params["priority"] = data.priority
        if data.schedule_delivery_time:
            params["sdt"] = data.schedule_delivery_time
        if data.validity_period:
            params["validity-period"] = data.validity_period
        if data.tags:
            params["tags"] = ",".join(str(t) for t in data.tags)

        try:
            resp = await _http_client().get("/send", params=params)
        except httpx.RequestError as exc:
            raise AppHttpException("Cannot reach Jasmin HTTP API", 503, {"endpoint": "/send", "error": str(exc)})

        body = resp.text.strip()
        if resp.status_code == 200 and body.startswith("Success"):
            # Format: 'Success "msgid"'
            msg_id = body.split('"')[1] if '"' in body else body.replace("Success", "").strip()
            return SmsSendOut(message_id=msg_id)

        if resp.status_code == 412:
            raise AppHttpException("No route found for the message", 422, {"username": data.username, "destination": data.to})
        if resp.status_code == 403:
            raise AppHttpException("Authentication failed or user quota exceeded", 403, {"username": data.username})

        # body is NOT forwarded — Jasmin may echo back request params (passwords) in error text
        raise AppHttpException("Jasmin rejected the message", 400, {"username": data.username, "destination": data.to, "http_status": resp.status_code})

    async def send_binary(self, data: SmsBinaryRequest) -> SmsSendOut:
        params: dict = {
            "username": data.username,
            "password": data.password,
            "to": data.to,
            "hex-content": data.hex_content,
            "coding": data.coding,
            "dlr": data.dlr,
        }
        if data.sender:
            params["from"] = data.sender
        if data.dlr_url:
            params["dlr-url"] = data.dlr_url
        if data.dlr_level is not None:
            params["dlr-level"] = data.dlr_level
        if data.dlr_method:
            params["dlr-method"] = data.dlr_method

        try:
            resp = await _http_client().get("/send", params=params)
        except httpx.RequestError as exc:
            raise AppHttpException("Cannot reach Jasmin HTTP API", 503, {"endpoint": "/send", "error": str(exc)})

        body = resp.text.strip()
        if resp.status_code == 200 and body.startswith("Success"):
            msg_id = body.split('"')[1] if '"' in body else body.replace("Success", "").strip()
            return SmsSendOut(message_id=msg_id)

        raise AppHttpException("Jasmin rejected the message", 400, {"username": data.username, "destination": data.to, "http_status": resp.status_code})

    async def rate(
        self,
        username: str,
        password: str,
        to: str,
        sender: str | None,
        content: str | None,
    ) -> SmsRateOut:
        params: dict = {"username": username, "password": password, "to": to}
        if sender:
            params["from"] = sender
        if content:
            params["content"] = content

        try:
            resp = await _http_client().get("/rate", params=params)
        except httpx.RequestError as exc:
            raise AppHttpException("Cannot reach Jasmin HTTP API", 503, {"endpoint": "/rate", "error": str(exc)})

        body = resp.text.strip()
        if resp.status_code == 200:
            # Jasmin ≥ 0.10: JSON {"unit_rate": 0.05, "submit_sm_count": 1}
            # Jasmin < 0.10:  text "Success '0.0' 'cid'"
            try:
                data = _json.loads(body)
                return SmsRateOut(
                    rate=float(data.get("unit_rate", 0.0)),
                    connector_id=None,
                )
            except (_json.JSONDecodeError, ValueError):
                pass
            parts = body.replace("'", "").split()
            rate_val = 0.0
            connector_id = None
            if len(parts) >= 2:
                try:
                    rate_val = float(parts[1])
                except ValueError:
                    pass
            if len(parts) >= 3:
                connector_id = parts[2]
            return SmsRateOut(rate=rate_val, connector_id=connector_id)

        if resp.status_code == 412:
            raise AppHttpException("No route found for this destination", 422, {"username": username, "destination": to})
        if resp.status_code == 403:
            raise AppHttpException("Authentication failed or user quota exceeded", 403, {"username": username})
        raise AppHttpException("Rate check failed", 400, {"username": username, "destination": to, "http_status": resp.status_code})

    async def balance(self, username: str, password: str) -> SmsBalanceOut:
        try:
            resp = await _http_client().get("/balance", params={"username": username, "password": password})
        except httpx.RequestError as exc:
            raise AppHttpException("Cannot reach Jasmin HTTP API", 503, {"endpoint": "/balance", "error": str(exc)})

        body = resp.text.strip()
        if resp.status_code == 200:
            # Jasmin ≥ 0.10: JSON {"balance": 50.0, "sms_count": "ND"}
            # Jasmin < 0.10:  text 'Success "100.0 500"'
            try:
                data = _json.loads(body)
                raw_balance = data.get("balance")
                raw_sms = data.get("sms_count")
                balance_val = float(raw_balance) if raw_balance is not None and str(raw_balance).upper() not in ("ND", "NONE") else None
                sms_count_val = None
                if raw_sms is not None and str(raw_sms).upper() not in ("ND", "NONE"):
                    try:
                        sms_count_val = int(raw_sms)
                    except (ValueError, TypeError):
                        pass
                return SmsBalanceOut(balance=balance_val, sms_count=sms_count_val)
            except (_json.JSONDecodeError, ValueError):
                pass
            # Legacy text format
            if body.startswith("Success"):
                inner = body.split('"')[1] if '"' in body else ""
                parts = inner.split()
                balance_val = None
                sms_count_val = None
                if len(parts) >= 1 and parts[0].upper() not in ("UD", "NONE", ""):
                    try:
                        balance_val = float(parts[0])
                    except ValueError:
                        pass
                if len(parts) >= 2 and parts[1].upper() not in ("UD", "NONE", ""):
                    try:
                        sms_count_val = int(parts[1])
                    except ValueError:
                        pass
                return SmsBalanceOut(balance=balance_val, sms_count=sms_count_val)

        if resp.status_code == 403:
            raise AppHttpException("Authentication failed", 403, {"username": username})
        raise AppHttpException("Balance check failed", 400, {"username": username, "http_status": resp.status_code})
