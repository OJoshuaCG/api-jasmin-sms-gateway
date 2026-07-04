"""
Parsers for Jasmin jcli text output.

jcli produces several output formats depending on the command:
  - List:  '#entity_id col2 ...' rows (no row numbers) + 'Total: N' footer
  - Show (space-kv):  'key value' lines (smppccm, user)
  - Show (eq-kv):    'key = value' lines (httpccm, filter with params)
  - Show (one-liner): 'Type to connector [rated N|NOT RATED]' (routes, interceptors)
  - Route/Interceptor list: '#order Type ...' rows (order in the # prefix)
"""

import re
from typing import Any

# ------------------------------------------------------------------ #
#  Generic helpers
# ------------------------------------------------------------------ #

def is_success(response: str) -> bool:
    # Error lines take priority
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
        if not stripped:
            continue
        if stripped.lower().startswith(("error", "failed", "unknown", "you must")):
            return stripped
    return response.strip() or "Unknown jcli error"


def parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "yes", "1", "enabled")


def parse_nullable(value: str) -> Any:
    """Return None for 'None'/'UD'/'ND'/'null'/'-', else the raw string."""
    if value.strip().lower() in ("none", "ud", "nd", "null", "-"):
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
#  Key-value helpers
# ------------------------------------------------------------------ #

def parse_space_kv(output: str) -> dict[str, str]:
    """Parse 'key value' space-separated pairs (smppccm show, user show).
    Handles empty values (single-token lines).
    """
    result: dict[str, str] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        key = parts[0]
        value = parts[1].strip() if len(parts) > 1 else ""
        result[key] = value
    return result


def parse_eq_kv(output: str) -> dict[str, str]:
    """Parse 'key = value' pairs (httpccm show, filter show with params)."""
    result: dict[str, str] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if " = " in stripped:
            key, _, value = stripped.partition(" = ")
            result[key.strip()] = value.strip()
    return result


def parse_kv(output: str) -> dict[str, str]:
    """Parse 'key   : value' pairs (legacy format, kept for compatibility)."""
    result: dict[str, str] = {}
    for line in output.splitlines():
        if " : " in line:
            key, _, value = line.partition(" : ")
            result[key.strip()] = value.strip()
    return result


# ------------------------------------------------------------------ #
#  List output parsers (no row numbers, '#entity_id ...' format)
# ------------------------------------------------------------------ #

def _parse_hash_rows(output: str, skip_starts: tuple[str, ...] = ()) -> list[list[str]]:
    """Extract rows from '#...' lines. Skips header lines matching skip_starts."""
    rows: list[list[str]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        parts = content.split()
        if not parts:
            continue
        # Skip header lines
        if skip_starts and parts[0].lower().startswith(skip_starts):
            continue
        rows.append(parts)
    return rows


def _parse_order_rows(output: str) -> list[tuple[int, list[str]]]:
    """Extract rows from '#N ...' lines where N is a numeric order.
    Returns list of (order, rest_parts).
    """
    rows: list[tuple[int, list[str]]] = []
    for line in output.splitlines():
        line = line.strip()
        m = re.match(r'^#(\d+)\s+(.*)', line)
        if not m:
            continue
        order = int(m.group(1))
        rest = m.group(2).split()
        rows.append((order, rest))
    return rows


# ------------------------------------------------------------------ #
#  Entity-specific parsers
# ------------------------------------------------------------------ #

def parse_group_list(output: str) -> list[dict]:
    """Parse 'group --list' output.

    Format: '#gid' per line for enabled groups, '#!gid' for disabled groups.
    Header line '#Group id' is skipped.
    """
    groups = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        raw = line[1:].strip()
        if not raw or raw.lower().startswith("group"):
            continue
        # Disabled groups are prefixed with '!'
        if raw.startswith("!"):
            groups.append({"gid": raw[1:].strip(), "enabled": False})
        else:
            groups.append({"gid": raw, "enabled": True})
    return groups


def parse_group_show(output: str) -> dict:
    kv = parse_kv(output)
    return {
        "gid": kv.get("gid", ""),
        "enabled": parse_bool(kv.get("enabled", "True")),
    }


def parse_user_list(output: str) -> list[dict]:
    """Parse 'user --list' output.

    Format: '#uid  gid  username  ...' per line (no row-number prefix).
    Disabled users appear as '#!uid'. Header line '#User id ...' is skipped.
    """
    users = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        raw = line[1:]
        enabled = True
        if raw.startswith("!"):
            enabled = False
            raw = raw[1:]
        parts = raw.split()
        if not parts or parts[0].lower() == "user":
            continue
        users.append({
            "uid": parts[0],
            "gid": parts[1] if len(parts) > 1 else "",
            "enabled": enabled,
        })
    return users


def parse_user_show(output: str) -> dict:
    """Parse 'user -s UID' output.

    Format: space-separated 'key value' (2 tokens) or
    'section subsection field value' (4 tokens).
    """
    top: dict[str, str] = {}
    nested: dict[str, dict[str, dict[str, str]]] = {}

    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2:
            top[parts[0]] = parts[1]
        elif len(parts) == 4:
            section, subsection, field, value = parts
            nested.setdefault(section, {}).setdefault(subsection, {})[field] = value

    mt_quota = nested.get("mt_messaging_cred", {}).get("quota", {})
    mt_auth = nested.get("mt_messaging_cred", {}).get("authorization", {})
    mt_vf = nested.get("mt_messaging_cred", {}).get("valuefilter", {})
    mt_dv = nested.get("mt_messaging_cred", {}).get("defaultvalue", {})
    smpps_auth = nested.get("smpps_cred", {}).get("authorization", {})
    smpps_quota = nested.get("smpps_cred", {}).get("quota", {})

    def g(d: dict, key: str, default: str = "ND") -> str:
        return d.get(key, default)

    return {
        "uid": top.get("uid", ""),
        "gid": top.get("gid", ""),
        "username": top.get("username", ""),
        "enabled": True,  # not exposed in user -s; updated via enable/disable

        # MT Quota — all under mt_messaging_cred quota
        "mt_throughput": parse_float_nullable(g(mt_quota, "http_throughput")),
        "smpps_throughput": parse_float_nullable(g(mt_quota, "smpps_throughput")),
        "balance": parse_float_nullable(g(mt_quota, "balance")),
        "sms_count": parse_int_nullable(g(mt_quota, "sms_count")),
        "mt_quota_early_percent": parse_float_nullable(g(mt_quota, "early_percent")),

        # MT Auth — all under mt_messaging_cred authorization
        "mt_auth_http_send": parse_bool(g(mt_auth, "http_send", "True")),
        "mt_auth_http_balance": parse_bool(g(mt_auth, "http_balance", "True")),
        "mt_auth_http_rate": parse_bool(g(mt_auth, "http_rate", "True")),
        "mt_auth_http_bulk": parse_bool(g(mt_auth, "http_bulk", "False")),
        "mt_auth_smpps_send": parse_bool(g(mt_auth, "smpps_send", "True")),
        "mt_auth_long_content": parse_bool(g(mt_auth, "http_long_content", "True")),
        "mt_auth_dlr_level": parse_bool(g(mt_auth, "dlr_level", "True")),
        "mt_auth_http_dlr_method": parse_bool(g(mt_auth, "http_dlr_method", "True")),
        "mt_auth_src_addr": parse_bool(g(mt_auth, "src_addr", "True")),
        "mt_auth_priority": parse_bool(g(mt_auth, "priority", "True")),
        "mt_auth_validity_period": parse_bool(g(mt_auth, "validity_period", "True")),
        "mt_auth_schedule_at": parse_bool(g(mt_auth, "schedule_delivery_time", "True")),
        "mt_auth_hex_content": parse_bool(g(mt_auth, "hex_content", "True")),

        # MT Value Filters — all under mt_messaging_cred valuefilter
        "mt_filter_src_addr": parse_nullable(g(mt_vf, "src_addr", "None")),
        "mt_filter_dst_addr": parse_nullable(g(mt_vf, "dst_addr", "None")),
        "mt_filter_content": parse_nullable(g(mt_vf, "content", "None")),
        "mt_filter_priority": parse_nullable(g(mt_vf, "priority", "None")),
        "mt_filter_validity_period": parse_nullable(g(mt_vf, "validity_period", "None")),

        # MT Default Values — under mt_messaging_cred defaultvalue
        "mt_default_src_addr": parse_nullable(g(mt_dv, "src_addr", "None")),

        # SMPP Server creds — under smpps_cred
        "smpps_allow_bind": parse_bool(g(smpps_auth, "bind", "True")),
        "smpps_max_bindings": parse_int_nullable(g(smpps_quota, "max_bindings")),
    }


def parse_smppccm_list(output: str) -> list[dict]:
    """Parse 'smppccm --list' — format: '#cid service session starts stops'."""
    connectors = []
    for row in _parse_hash_rows(output, skip_starts=("connector",)):
        if not row:
            continue
        connectors.append({
            "cid": row[0],
            "status": row[1].lower() if len(row) > 1 else "unknown",
            "sessions_count": int(row[2]) if len(row) > 2 and row[2].isdigit() else 0,
        })
    return connectors


def parse_smppccm_show(output: str) -> dict:
    """Parse 'smppccm -s CID' output (space-separated key value pairs).

    Jasmin field names differ from the API schema:
      bind (type) → bind_to in schema
      systype     → system_type
      addr_range  → address_range
      src_ton     → source_addr_ton
      src_npi     → source_addr_npi
      dst_ton     → dest_addr_ton
      dst_npi     → dest_addr_npi
      con_loss_retry  → reconnect_on_connection_loss
      con_loss_delay  → reconnect_on_connection_loss_delay
      con_fail_retry  → reconnect_on_connection_failure
      con_fail_delay  → reconnect_on_connection_failure_delay
    """
    kv = parse_space_kv(output)
    return {
        "cid": kv.get("cid", ""),
        "host": kv.get("host", ""),
        "port": int(kv.get("port", "2775") or "2775"),
        "username": kv.get("username", ""),
        "bind_to": kv.get("bind", "transceiver"),
        "system_type": parse_nullable(kv.get("systype", "") or "None"),
        "interface_version": "34",
        "address_range": parse_nullable(kv.get("addr_range", "None") or "None"),
        "source_addr_ton": parse_int_nullable(kv.get("src_ton", "None") or "None"),
        "source_addr_npi": parse_int_nullable(kv.get("src_npi", "None") or "None"),
        "dest_addr_ton": parse_int_nullable(kv.get("dst_ton", "None") or "None"),
        "dest_addr_npi": parse_int_nullable(kv.get("dst_npi", "None") or "None"),
        "submit_throughput": parse_float_nullable(kv.get("submit_throughput", "None") or "None"),
        "dlr_expiry": parse_int_nullable(kv.get("dlr_expiry", "None") or "None"),
        "reconnect_on_connection_loss": parse_bool(kv.get("con_loss_retry", "yes")),
        "reconnect_on_connection_loss_delay": int(kv.get("con_loss_delay", "10") or "10"),
        "reconnect_on_connection_failure": parse_bool(kv.get("con_fail_retry", "yes")),
        "reconnect_on_connection_failure_delay": int(kv.get("con_fail_delay", "10") or "10"),
    }


def parse_httpccm_list(output: str) -> list[dict]:
    """Parse 'httpccm --list' — format: '#cid type method url'."""
    connectors = []
    for row in _parse_hash_rows(output, skip_starts=("httpcc",)):
        if not row:
            continue
        connectors.append({
            "cid": row[0],
            "method": row[2] if len(row) > 2 else "",
            "url": row[3] if len(row) > 3 else "",
        })
    return connectors


def parse_httpccm_show(output: str) -> dict:
    """Parse 'httpccm -s CID' output (key = value format).

    Jasmin uses 'baseurl' internally; the API exposes it as 'url'.
    """
    kv = parse_eq_kv(output)
    return {
        "cid": kv.get("cid", ""),
        "url": kv.get("baseurl", kv.get("url", "")),
        "method": kv.get("method", "GET"),
    }


def _parse_filter_description_params(description: str) -> dict:
    """Extract params from jcli filter description, e.g. '<U (uid=pbxsmpp)>'.

    Handles patterns like:
      <U (uid=value)>          → {uid: value}
      <C (cid=value)>          → {cid: value}
      <SA (source_addr=value)> → {source_addr: value}
      <T>                      → {}  (TransparentFilter, no params)
    Values may contain spaces (e.g. regex patterns), so we capture until ')'.
    """
    params: dict = {}
    # Find all key=value pairs inside parentheses within angle brackets
    for key, val in re.findall(r'(\w+)=([^)]+)', description):
        params[key] = val.strip()
    return params


def parse_filter_list(output: str) -> list[dict]:
    """Parse 'filter --list' — columns: fid, type, routes, description.

    'Routes' can be multi-token (e.g. 'MO MT'). The description always starts
    with '<', so we split on the first '<' to avoid misclassifying route tokens
    as part of the description.
    """
    filters = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        content = line[1:]
        # Skip the header row ('#Filter id  Type ...')
        if re.match(r'filter\s+id', content, re.IGNORECASE):
            continue
        # Split at first '<': left side has fid+type+routes, right side is description
        if "<" in content:
            left, _, right = content.partition("<")
            description = ("<" + right).strip()
        else:
            left = content
            description = ""
        parts = left.split()
        if len(parts) < 2:
            continue
        fid = parts[0]
        type_ = parts[1]
        routes = " ".join(parts[2:]).strip()
        filters.append({
            "fid": fid,
            "type": type_,
            "routes": routes,
            "description": description,
            "params": _parse_filter_description_params(description),
        })
    return filters


def parse_filter_show(output: str) -> dict:
    """Parse 'filter -s FID' output.

    Simple filters (e.g. TransparentFilter): just the type name on one line.
    Parametrized filters: 'TypeName:' then 'key = value' lines.
    Returns {'type': ..., 'params': {...}} — fid must be added by the caller.
    """
    type_name = ""
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip the command echo line and 'jcli :' prompt
        if stripped.startswith(("filter", "jcli")):
            continue
        # First matching line is the type
        if stripped[0].isupper():
            type_name = stripped.rstrip(":")
            break

    params = parse_eq_kv(output)
    return {"type": type_name, "params": params}


def parse_route_list(output: str) -> list[dict]:
    """Parse mtrouter/morouter --list.

    Format: '#order Type Rate Connector Filter(s)'
    The '#order' prefix contains the numeric route order.
    filter_raw captures the raw Jasmin filter indicator (e.g. '<T>' for TransparentFilter).
    """
    routes = []
    for line in output.splitlines():
        line = line.strip()
        m = re.match(r'^#(\d+)\s+(.*)', line)
        if not m:
            continue
        order = int(m.group(1))
        rest = m.group(2).split()
        type_ = rest[0] if rest else ""
        # Filter indicator is the last angle-bracket token on the line, if present
        filter_raw = ""
        bracket = re.search(r'(<[^>]+>)\s*$', m.group(2))
        if bracket:
            filter_raw = bracket.group(1)
        routes.append({"order": order, "type": type_, "filter_raw": filter_raw})
    return routes


def parse_mt_route_show(output: str, order: int) -> dict:
    """Parse 'mtrouter -s ORDER' one-liner.

    Format: 'Type to connector [rated N.NN|NOT RATED]'
    """
    for line in output.splitlines():
        line = line.strip()
        m = re.match(r'^(\w+)\s+to\s+(\S+)\s+(NOT RATED|rated\s+([\d.]+))', line)
        if m:
            rate_str = m.group(4)
            return {
                "order": order,
                "type": m.group(1),
                "connectors": [m.group(2)],
                "filters": [],
                "rate": float(rate_str) if rate_str else None,
            }
    return {"order": order, "type": "", "connectors": [], "filters": [], "rate": None}


def parse_mo_route_show(output: str, order: int) -> dict:
    """Parse 'morouter -s ORDER' one-liner.

    Format: 'Type to connector [NOT RATED|rated N.NN]'
    """
    for line in output.splitlines():
        line = line.strip()
        m = re.match(r'^(\w+)\s+to\s+(\S+)', line)
        if m:
            return {
                "order": order,
                "type": m.group(1),
                "connector": m.group(2),
                "filters": [],
            }
    return {"order": order, "type": "", "connector": "", "filters": []}


def parse_route_show(output: str) -> dict:
    """Legacy alias — returns raw kv from output (kept for compatibility)."""
    return parse_kv(output)


def parse_interceptor_list(output: str) -> list[dict]:
    """Parse mtinterceptor/mointerceptor --list.

    Format: '#order Type Script Filter(s)'
    The '#order' prefix contains the numeric interceptor order.
    """
    interceptors = []
    for order, rest in _parse_order_rows(output):
        type_ = rest[0] if rest else ""
        interceptors.append({"order": order, "type": type_})
    return interceptors


def parse_interceptor_show(output: str) -> dict:
    """Parse 'mtinterceptor -s ORDER' / 'mointerceptor -s ORDER' one-liner.

    Format: 'Type/<script_repr>'
    Script path cannot be recovered from this output.
    """
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("mtinterceptor", "mointerceptor", "jcli")):
            continue
        if "/" in stripped:
            type_ = stripped.split("/")[0]
            return {"type": type_}
    return {"type": ""}


def parse_smppserver_show(output: str) -> dict:
    kv = parse_kv(output)
    return {
        "host": kv.get("host", "0.0.0.0"),
        "port": int(kv.get("port", "2775") or "2775"),
        "max_bindings": parse_int_nullable(kv.get("max_bindings", "UD") or "UD"),
    }


def _parse_stats_hash_kv(output: str) -> dict[str, str]:
    """Parse stats output: '#Key   Value' lines (hash-prefixed key-value pairs)."""
    result: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        parts = content.split(None, 1)
        if len(parts) == 2:
            result[parts[0]] = parts[1].strip()
        elif len(parts) == 1:
            result[parts[0]] = ""
    return result


def parse_stats_smppc(output: str, cid: str) -> dict:
    """Parse 'stats --smppc=CID' output (#Item Value format)."""
    kv = _parse_stats_hash_kv(output)
    return {
        "cid": cid,
        "created_at": parse_nullable(kv.get("created_at", "ND")),
        "connected_at": parse_nullable(kv.get("connected_at", "ND")),
        "bound_at": parse_nullable(kv.get("bound_at", "ND")),
        "disconnected_at": parse_nullable(kv.get("disconnected_at", "ND")),
        "last_received_pdu_at": parse_nullable(kv.get("last_received_pdu_at", "ND")),
        "last_sent_pdu_at": parse_nullable(kv.get("last_sent_pdu_at", "ND")),
        "connected_count": int(kv.get("connected_count", "0") or "0"),
        "bound_count": int(kv.get("bound_count", "0") or "0"),
        "disconnected_count": int(kv.get("disconnected_count", "0") or "0"),
        "submit_sm_request_count": int(kv.get("submit_sm_request_count", "0") or "0"),
        "submit_sm_count": int(kv.get("submit_sm_count", "0") or "0"),
        "deliver_sm_count": int(kv.get("deliver_sm_count", "0") or "0"),
        "elink_count": int(kv.get("elink_count", "0") or "0"),
        "throttling_error_count": int(kv.get("throttling_error_count", "0") or "0"),
        "other_submit_error_count": int(kv.get("other_submit_error_count", "0") or "0"),
        "interceptor_error_count": int(kv.get("interceptor_error_count", "0") or "0"),
        "interceptor_count": int(kv.get("interceptor_count", "0") or "0"),
    }


def parse_stats_smppcs(output: str) -> list[dict]:
    """Parse 'stats --smppcs' tabular output.

    Format: #cid  Connected_at  Bound_at  Disconnected_at  Submits  Delivers  QoS_errs  Other_errs
    Header row starts with '#Connector'.
    """
    rows = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        content = line[1:].strip()
        if not content or content.lower().startswith("connector"):
            continue
        parts = content.split()
        if not parts:
            continue
        rows.append({
            "cid": parts[0],
            "connected_at": parse_nullable(parts[1]) if len(parts) > 1 else None,
            "bound_at": parse_nullable(parts[2]) if len(parts) > 2 else None,
            "disconnected_at": parse_nullable(parts[3]) if len(parts) > 3 else None,
            "submits": parts[4] if len(parts) > 4 else "0/0",
            "delivers": parts[5] if len(parts) > 5 else "0/0",
            "qos_errors": int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else 0,
            "other_errors": int(parts[7]) if len(parts) > 7 and parts[7].isdigit() else 0,
        })
    return rows


def parse_stats_user(output: str, uid: str) -> dict:
    """Parse 'stats --user=UID' output.

    Format: '#Item   Type   Value' (3 columns).
    Items are grouped by Type: 'SMPP Server' and 'HTTP Api'.
    bound_connections_count value is a JSON dict — extract the total.
    """
    smpp: dict[str, str] = {}
    http: dict[str, str] = {}

    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        content = line[1:].strip()
        if not content or content.lower().startswith("item"):
            continue
        # Split into at most 3 parts: item, type_prefix, value
        # Type is 2 words ("SMPP Server" or "HTTP Api"), so we split differently
        if "SMPP Server" in content:
            key = content.split("SMPP Server")[0].strip()
            val = content.split("SMPP Server", 1)[1].strip()
            smpp[key] = val
        elif "HTTP Api" in content:
            key = content.split("HTTP Api")[0].strip()
            val = content.split("HTTP Api", 1)[1].strip()
            http[key] = val

    def _int(d: dict, k: str) -> int:
        v = d.get(k, "0").strip()
        # Handle JSON dict values like {"bind_receiver": 0, ...} — sum values
        if v.startswith("{"):
            try:
                import json
                obj = json.loads(v)
                return sum(obj.values()) if isinstance(obj, dict) else 0
            except Exception:
                return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    return {
        "uid": uid,
        "smpp_bind_count": _int(smpp, "bind_count"),
        "smpp_unbind_count": _int(smpp, "unbind_count"),
        "smpp_bound_connections": _int(smpp, "bound_connections_count"),
        "smpp_submit_sm_request_count": _int(smpp, "submit_sm_request_count"),
        "smpp_submit_sm_count": _int(smpp, "submit_sm_count"),
        "smpp_deliver_sm_count": _int(smpp, "deliver_sm_count"),
        "smpp_elink_count": _int(smpp, "elink_count"),
        "smpp_throttling_error_count": _int(smpp, "throttling_error_count"),
        "smpp_other_submit_error_count": _int(smpp, "other_submit_error_count"),
        "smpp_last_activity_at": parse_nullable(smpp.get("last_activity_at", "ND")),
        "http_connects_count": _int(http, "connects_count"),
        "http_submit_sm_request_count": _int(http, "submit_sm_request_count"),
        "http_balance_request_count": _int(http, "balance_request_count"),
        "http_rate_request_count": _int(http, "rate_request_count"),
        "http_last_activity_at": parse_nullable(http.get("last_activity_at", "ND")),
    }


def parse_stats_users(output: str) -> list[dict]:
    """Parse 'stats --users' tabular output.

    Format: #uid  SMPP_Bound  SMPP_LA  HTTP_requests  HTTP_LA
    Header row starts with '#User'.
    """
    rows = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        content = line[1:].strip()
        if not content or content.lower().startswith("user"):
            continue
        parts = content.split()
        if not parts:
            continue
        rows.append({
            "uid": parts[0],
            "smpp_bound_connections": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
            "smpp_last_activity": parse_nullable(parts[2]) if len(parts) > 2 else None,
            "http_request_count": int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0,
            "http_last_activity": parse_nullable(parts[4]) if len(parts) > 4 else None,
        })
    return rows


def parse_stats_httpapi(output: str) -> dict:
    """Parse 'stats --httpapi' output (#Item Value format)."""
    kv = _parse_stats_hash_kv(output)
    return {
        "created_at": parse_nullable(kv.get("created_at", "ND")),
        "last_request_at": parse_nullable(kv.get("last_request_at", "ND")),
        "last_success_at": parse_nullable(kv.get("last_success_at", "ND")),
        "request_count": int(kv.get("request_count", "0") or "0"),
        "success_count": int(kv.get("success_count", "0") or "0"),
        "auth_error_count": int(kv.get("auth_error_count", "0") or "0"),
        "route_error_count": int(kv.get("route_error_count", "0") or "0"),
        "interceptor_error_count": int(kv.get("interceptor_error_count", "0") or "0"),
        "interceptor_count": int(kv.get("interceptor_count", "0") or "0"),
        "throughput_error_count": int(kv.get("throughput_error_count", "0") or "0"),
        "charging_error_count": int(kv.get("charging_error_count", "0") or "0"),
        "server_error_count": int(kv.get("server_error_count", "0") or "0"),
    }


def parse_stats_smppsapi(output: str) -> dict:
    """Parse 'stats --smppsapi' output (#Item Value format)."""
    kv = _parse_stats_hash_kv(output)
    return {
        "created_at": parse_nullable(kv.get("created_at", "ND")),
        "last_received_pdu_at": parse_nullable(kv.get("last_received_pdu_at", "ND")),
        "last_sent_pdu_at": parse_nullable(kv.get("last_sent_pdu_at", "ND")),
        "connected_count": int(kv.get("connected_count", "0") or "0"),
        "connect_count": int(kv.get("connect_count", "0") or "0"),
        "disconnect_count": int(kv.get("disconnect_count", "0") or "0"),
        "bound_trx_count": int(kv.get("bound_trx_count", "0") or "0"),
        "bound_rx_count": int(kv.get("bound_rx_count", "0") or "0"),
        "bound_tx_count": int(kv.get("bound_tx_count", "0") or "0"),
        "bind_trx_count": int(kv.get("bind_trx_count", "0") or "0"),
        "bind_rx_count": int(kv.get("bind_rx_count", "0") or "0"),
        "bind_tx_count": int(kv.get("bind_tx_count", "0") or "0"),
        "unbind_count": int(kv.get("unbind_count", "0") or "0"),
        "submit_sm_request_count": int(kv.get("submit_sm_request_count", "0") or "0"),
        "submit_sm_count": int(kv.get("submit_sm_count", "0") or "0"),
        "deliver_sm_count": int(kv.get("deliver_sm_count", "0") or "0"),
        "elink_count": int(kv.get("elink_count", "0") or "0"),
        "throttling_error_count": int(kv.get("throttling_error_count", "0") or "0"),
        "other_submit_error_count": int(kv.get("other_submit_error_count", "0") or "0"),
        "interceptor_error_count": int(kv.get("interceptor_error_count", "0") or "0"),
        "interceptor_count": int(kv.get("interceptor_count", "0") or "0"),
    }
