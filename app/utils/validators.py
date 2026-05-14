"""
Shared Pydantic field validators for security-sensitive fields.

These validators are the first line of defense against jcli command injection.
The second line is jasmin_telnet._sanitize(), which strips control chars at
the wire level regardless of schema validation.
"""
import re

# Strict identifier: only letters, digits, underscores, hyphens.
# Used for fid, gid, cid, uid — values that appear directly in jcli commands.
_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

# Control characters that can escape jcli interactive sessions when injected
# into field values: CR, LF, NUL.
_CONTROL_CHARS = {'\r', '\n', '\x00'}


def validate_identifier(v: str, field_name: str = "field") -> str:
    """Allow only [a-zA-Z0-9_-]. Blocks all telnet injection chars."""
    if not _ID_RE.match(v):
        raise ValueError(f"{field_name} only allows letters, digits, underscores and hyphens")
    return v


def validate_no_control_chars(v: str, field_name: str = "field") -> str:
    """Block CR, LF and NUL — sufficient to prevent jcli interactive mode escape."""
    if any(c in v for c in _CONTROL_CHARS):
        raise ValueError(f"{field_name} must not contain CR, LF or NUL characters")
    return v
