"""
Parsers for Jasmin jcli text output.

jcli produces two main output formats:
  - List:  header + '#N id col2 ...' rows + 'Total: N ...' footer
  - Show:  'key   : value' lines, optionally with nested section headers
"""

import re
from typing import Any

# ------------------------------------------------------------------ #
#  Generic helpers
# ------------------------------------------------------------------ #

def is_success(response: str) -> bool:
    # Error lines take priority — a message like "Error: connector already started"
    # must not be treated as success just because "started" appears in it.
    for line in response.splitlines():
        if line.strip().lower().startswith("error"):
            return False
    lower = response.lower()
    return any(
        token in lower
        for token in (
            "success",
            "adding a new",
            "updating",
            "removing",
            "started",
            "stopped",
            "flushed",
            "persistence storage updated",
            "total:",
        )
    )


def extract_error_message(response: str) -> str:
    for line in response.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(("error", "failed", "unknown")):
            return stripped
    return response.strip() or "Unknown jcli error"


def parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "yes", "1", "enabled")


def parse_nullable(value: str) -> Any:
    """Return None for 'None'/'UD'/'null', else the raw string."""
    if value.strip().lower() in ("none", "ud", "null", "-"):
        return None
    return value.strip()


def parse_float_nullable(value: str) -> float | None:
    v = parse_nullable(value)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_int_nullable(value: str) -> int | None:
    v = parse_nullable(value)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


# ------------------------------------------------------------------ #
#  List output parser
# ------------------------------------------------------------------ #

def parse_list_ids(output: str) -> list[str]:
    """
    Extract IDs from '--list' output.  Lines look like:
        #1 myid    other_columns...
    Returns the second token (after '#N') as the ID.
    """
    ids: list[str] = []
    for line in output.splitlines():
        line = line.strip()
        if re.match(r"^#\d+\s+", line):
            parts = line.split()
            if len(parts) >= 2:
                ids.append(parts[1])
    return ids


def parse_list_rows(output: str) -> list[list[str]]:
    """
    Extract all data rows as token lists (excluding the '#N' prefix).
    Used when multiple columns are needed.
    """
    rows: list[list[str]] = []
    for line in output.splitlines():
        line = line.strip()
        if re.match(r"^#\d+\s+", line):
            parts = line.split()
            rows.append(parts[1:])  # skip '#N'
    return rows


# ------------------------------------------------------------------ #
#  Key-value show parser
# ------------------------------------------------------------------ #

def parse_kv(output: str) -> dict[str, str]:
    """
    Parse simple 'key   : value' pairs into a flat dict.
    Section headers (lines without ' : ') are ignored.
    """
    result: dict[str, str] = {}
    for line in output.splitlines():
        if " : " in line:
            key, _, value = line.partition(" : ")
            result[key.strip()] = value.strip()
    return result


def parse_nested_kv(output: str) -> dict[str, Any]:
    """
    Parse jcli 'show' output with up to two levels of nested sections.

    Indentation determines depth:
      indent == 0  → top-level k:v or top-level section header
      indent  > 0, current section set → sub-section header or k:v inside section/subsection
    """
    result: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None
    current_subsection: dict[str, str] | None = None

    for line in output.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if " : " in stripped:
            key, _, value = stripped.partition(" : ")
            kv = {key.strip(): value.strip()}
            if current_subsection is not None:
                current_subsection.update(kv)
            elif current_section is not None:
                current_section.update(kv)
            else:
                result.update(kv)
        elif stripped.endswith(":") and " : " not in stripped:
            name = stripped.rstrip(":")
            if indent == 0 or current_section is None:
                # Top-level section — resets sub-section context
                current_section = {}
                result[name] = current_section
                current_subsection = None
            else:
                # Sub-section inside the current top-level section
                current_subsection = {}
                current_section[name] = current_subsection
        # else: ignore decorative separator lines

    return result


# ------------------------------------------------------------------ #
#  Entity-specific parsers
# ------------------------------------------------------------------ #

def parse_group_list(output: str) -> list[dict]:
    """Parse 'group --list' output."""
    groups = []
    for row in parse_list_rows(output):
        if not row:
            continue
        groups.append({
            "gid": row[0],
            "enabled": parse_bool(row[1]) if len(row) > 1 else True,
        })
    return groups


def parse_group_show(output: str) -> dict:
    kv = parse_kv(output)
    return {
        "gid": kv.get("gid", ""),
        "enabled": parse_bool(kv.get("enabled", "True")),
    }


def parse_user_list(output: str) -> list[dict]:
    """Parse 'user --list' — columns: uid, gid, enabled."""
    users = []
    for row in parse_list_rows(output):
        if len(row) < 1:
            continue
        users.append({
            "uid": row[0],
            "gid": row[1] if len(row) > 1 else "",
            "enabled": parse_bool(row[2]) if len(row) > 2 else True,
        })
    return users


def _find_section(kv: dict, *prefixes: str) -> dict:
    """Return the first dict value whose key starts with any of the given prefixes (case-insensitive)."""
    for key, val in kv.items():
        for prefix in prefixes:
            if key.lower().startswith(prefix.lower()):
                return val if isinstance(val, dict) else {}
    return {}


def parse_user_show(output: str) -> dict:
    """Parse 'user --show' nested output.

    Jasmin section names vary slightly across versions; _find_section() matches
    by prefix so "MT Messaging" and "MT Messaging cred" both resolve correctly.
    """
    kv = parse_nested_kv(output)

    mt = _find_section(kv, "MT Messaging", "mt messaging")
    mt_quota = _find_section(mt, "quota")
    mt_auth = _find_section(mt, "authorization", "auth")
    mt_vf = _find_section(mt, "value_filter", "valuefilter", "value filter")

    smpps = _find_section(kv, "SMPPS", "SMPP Server", "smpp server")
    smpps_auth = _find_section(smpps, "authorization", "auth")
    smpps_quota = _find_section(smpps, "quota")

    def _g(d: dict, key: str, default: str = "") -> str:
        return str(d.get(key, default))

    return {
        "uid": str(kv.get("uid", "")),
        "gid": str(kv.get("gid", "")),
        "enabled": str(kv.get("status", "Enabled")).lower() == "enabled",
        "mt_throughput": parse_float_nullable(_g(mt_quota, "http_throughput", "UD")),
        "mo_throughput": None,
        "balance": parse_float_nullable(_g(mt_quota, "balance", "UD")),
        "sms_count": parse_int_nullable(_g(mt_quota, "sms_count", "UD")),
        "mt_auth_priority": parse_bool(_g(mt_auth, "priority", "True")),
        "mt_auth_validity_period": parse_bool(_g(mt_auth, "validity_period", "True")),
        "mt_auth_src_addr": parse_bool(_g(mt_auth, "src_addr", "True")),
        "mt_auth_schedule_at": parse_bool(_g(mt_auth, "schedule_at", "True")),
        "mt_auth_dlr_level": parse_bool(_g(mt_auth, "dlr_level", "True")),
        # Jasmin stores this as "http_long_content" in the authorization sub-section
        "mt_auth_long_content": parse_bool(_g(mt_auth, "http_long_content", "True")),
        "mt_filter_src_addr": parse_nullable(_g(mt_vf, "src_addr", "None")),
        "mt_filter_dst_addr": parse_nullable(_g(mt_vf, "dst_addr", "None")),
        "mt_filter_content": parse_nullable(_g(mt_vf, "content", "None")),
        "smpps_allow_bind": parse_bool(_g(smpps_auth, "bind", "True")),
        "smpps_max_bindings": parse_int_nullable(_g(smpps_quota, "max_bindings", "UD")),
        # Jasmin stores this as "quota_sms_count" (not "sms_count") inside the SMPPS quota
        "smpps_quota_sms_count": parse_int_nullable(_g(smpps_quota, "quota_sms_count", "UD")),
        "smpps_throughput": parse_float_nullable(_g(smpps_quota, "throughput", "UD")),
    }


def parse_smppccm_list(output: str) -> list[dict]:
    """Parse 'smppccm --list' — columns: cid, service_status, sessions_count."""
    connectors = []
    for row in parse_list_rows(output):
        if not row:
            continue
        connectors.append({
            "cid": row[0],
            "status": row[1].lower() if len(row) > 1 else "unknown",
            "sessions_count": int(row[2]) if len(row) > 2 and row[2].isdigit() else 0,
        })
    return connectors


def parse_smppccm_show(output: str) -> dict:
    kv = parse_kv(output)
    return {
        "cid": kv.get("cid", ""),
        "host": kv.get("host", ""),
        "port": int(kv.get("port", "2775") or "2775"),
        "username": kv.get("username", ""),
        "bind_to": kv.get("bind_to", "transceiver"),
        "system_type": parse_nullable(kv.get("system_type", "None") or "None"),
        "interface_version": kv.get("interface_version", "34"),
        "address_range": parse_nullable(kv.get("address_range", "None") or "None"),
        "source_addr_ton": parse_int_nullable(kv.get("source_addr_ton", "None") or "None"),
        "source_addr_npi": parse_int_nullable(kv.get("source_addr_npi", "None") or "None"),
        "dest_addr_ton": parse_int_nullable(kv.get("dest_addr_ton", "None") or "None"),
        "dest_addr_npi": parse_int_nullable(kv.get("dest_addr_npi", "None") or "None"),
        "submit_throughput": parse_float_nullable(kv.get("submit_throughput", "None") or "None"),
        "dlr_expiry": parse_int_nullable(kv.get("dlr_expiry", "None") or "None"),
        "reconnect_on_connection_loss": parse_bool(kv.get("reconnect_on_connection_loss", "True")),
        "reconnect_on_connection_loss_delay": int(kv.get("reconnect_on_connection_loss_delay", "10") or "10"),
        "reconnect_on_connection_failure": parse_bool(kv.get("reconnect_on_connection_failure", "True")),
        "reconnect_on_connection_failure_delay": int(kv.get("reconnect_on_connection_failure_delay", "10") or "10"),
    }


def parse_httpccm_list(output: str) -> list[dict]:
    connectors = []
    for row in parse_list_rows(output):
        if not row:
            continue
        connectors.append({
            "cid": row[0],
            "method": row[1] if len(row) > 1 else "",
            "url": row[2] if len(row) > 2 else "",
        })
    return connectors


def parse_httpccm_show(output: str) -> dict:
    kv = parse_kv(output)
    return {
        "cid": kv.get("cid", ""),
        "url": kv.get("url", ""),
        "method": kv.get("method", "GET"),
    }


def parse_filter_list(output: str) -> list[dict]:
    filters = []
    for row in parse_list_rows(output):
        if not row:
            continue
        filters.append({
            "fid": row[0],
            "type": row[1] if len(row) > 1 else "",
        })
    return filters


def parse_filter_show(output: str) -> dict:
    kv = parse_kv(output)
    params = {}
    skip_keys = {"fid", "type"}
    for k, v in kv.items():
        if k not in skip_keys:
            params[k] = v
    return {
        "fid": kv.get("fid", ""),
        "type": kv.get("type", ""),
        "params": params,
    }


def parse_route_list(output: str) -> list[dict]:
    """Parse mtrouter/morouter --list — columns: order, type, ..."""
    routes = []
    for row in parse_list_rows(output):
        if not row:
            continue
        routes.append({
            "order": int(row[0]) if row[0].isdigit() else 0,
            "type": row[1] if len(row) > 1 else "",
        })
    return routes


def parse_route_show(output: str) -> dict:
    kv = parse_kv(output)
    return kv


def parse_interceptor_list(output: str) -> list[dict]:
    interceptors = []
    for row in parse_list_rows(output):
        if not row:
            continue
        interceptors.append({
            "order": int(row[0]) if row[0].isdigit() else 0,
            "type": row[1] if len(row) > 1 else "",
        })
    return interceptors


def parse_interceptor_show(output: str) -> dict:
    kv = parse_kv(output)
    return kv


def parse_smppserver_show(output: str) -> dict:
    kv = parse_kv(output)
    return {
        "host": kv.get("host", "0.0.0.0"),
        "port": int(kv.get("port", "2775") or "2775"),
        "max_bindings": parse_int_nullable(kv.get("max_bindings", "UD") or "UD"),
    }


def parse_stats_global(output: str) -> dict:
    kv = parse_kv(output)
    return kv


def parse_stats_smppccm(output: str, cid: str) -> dict:
    kv = parse_kv(output)
    return {
        "cid": cid,
        "status": kv.get("status", "unknown"),
        "sent_count": parse_int_nullable(kv.get("sent_count", "0")) or 0,
        "received_count": parse_int_nullable(kv.get("received_count", "0")) or 0,
        "error_count": parse_int_nullable(kv.get("error_count", "0")) or 0,
        "last_activity_at": parse_nullable(kv.get("last_activity_at", "None")),
    }


def parse_stats_user(output: str, uid: str) -> dict:
    kv = parse_kv(output)
    return {
        "uid": uid,
        "mt_count": parse_int_nullable(kv.get("mt_count", "0")) or 0,
        "mo_count": parse_int_nullable(kv.get("mo_count", "0")) or 0,
        "last_activity_at": parse_nullable(kv.get("last_activity_at", "None")),
    }
