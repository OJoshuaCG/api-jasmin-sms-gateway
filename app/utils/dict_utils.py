_SENSITIVE_KEYS = {"password", "hashed_password", "secret", "token", "key", "pass"}


def _sanitize_dict(data: dict) -> dict:
    """
    Remueve o enmascara valores sensibles de un diccionario antes de loguearlo.
    Las claves que coincidan con _SENSITIVE_KEYS se reemplazan con '***'.
    """
    if not isinstance(data, dict):
        return data
    return {
        k: "***" if k.lower() in _SENSITIVE_KEYS else v for k, v in data.items()
    }
