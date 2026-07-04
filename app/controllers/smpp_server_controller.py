"""
SMPP Server configuration is managed via Jasmin's config file (/etc/jasmin/jasmin.cfg),
not via jcli telnet. This controller reads the config file directly.
Updates require editing the config file and restarting Jasmin; PATCH is not supported.
"""

import configparser
import re

from app.exceptions import AppHttpException
from app.schemas.smpp_server import SmppServerOut

_JASMIN_CFG = "/etc/jasmin/jasmin.cfg"

# Jasmin defaults for [smpp-server] section
_DEFAULTS = {
    "bind": "0.0.0.0",
    "port": "2775",
    "max_bindings": None,
}


def _read_smppserver_config() -> dict:
    """Read [smpp-server] from jasmin.cfg.

    configparser ignores commented-out lines, so uncommented values take
    precedence; everything else falls back to Jasmin's built-in defaults.
    """
    cfg = configparser.ConfigParser()
    cfg.read(_JASMIN_CFG)

    section = cfg["smpp-server"] if "smpp-server" in cfg else {}

    raw_port = section.get("port", _DEFAULTS["port"])
    try:
        port = int(raw_port)
    except (ValueError, TypeError):
        port = 2775

    raw_max = section.get("max_bindings", None)
    max_bindings: int | None = None
    if raw_max is not None:
        try:
            max_bindings = int(raw_max)
        except (ValueError, TypeError):
            max_bindings = None

    return {
        "host": section.get("bind", _DEFAULTS["bind"]),
        "port": port,
        "max_bindings": max_bindings,
    }


class SmppServerController:

    async def get_config(self) -> SmppServerOut:
        try:
            data = _read_smppserver_config()
        except Exception as exc:
            raise AppHttpException(
                "Failed to read SMPP server configuration",
                500,
                {"config_file": _JASMIN_CFG, "error": str(exc)},
            ) from exc
        return SmppServerOut(**data)

