import logging
import logging.handlers
import re
from pathlib import Path

from app.core.environments import APP_NAME, LOGGER_JCLI_WARNINGS_FILE, LOGGER_LEVEL

_SENSITIVE_QS_PARAMS = re.compile(r'(?i)(?<=[?&])password=[^&\s"]*')


class _SensitiveDataFilter(logging.Filter):
    """Strips password values from uvicorn access log lines that contain raw URLs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.getMessage and isinstance(record.args, tuple):
            record.args = tuple(
                _SENSITIVE_QS_PARAMS.sub("password=***", str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True


_jcli_warnings_logger: logging.Logger | None = None


def get_jcli_warnings_logger() -> logging.Logger:
    """Logger dedicado a registrar advertencias de claves desconocidas en jcli.

    Escribe en consola Y en un archivo rotativo (LOGGER_JCLI_WARNINGS_FILE).
    Solo captura WARNING+; no eleva errores al caller.
    """
    global _jcli_warnings_logger
    if _jcli_warnings_logger is not None:
        return _jcli_warnings_logger

    lg = logging.getLogger("jcli.warnings")
    lg.setLevel(logging.WARNING)
    lg.propagate = False

    if not lg.hasHandlers():
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        # Console
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        lg.addHandler(ch)

        # Rotating file
        log_path = Path(LOGGER_JCLI_WARNINGS_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB por archivo
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        lg.addHandler(fh)

    _jcli_warnings_logger = lg
    return lg


def _apply_sensitive_filter() -> None:
    """Attach the filter to uvicorn access loggers so query-string passwords are redacted."""
    for logger_name in ("uvicorn.access", "uvicorn"):
        lg = logging.getLogger(logger_name)
        if not any(isinstance(f, _SensitiveDataFilter) for f in lg.filters):
            lg.addFilter(_SensitiveDataFilter())


def get_logger(
    name: str | None = None, level: str | int | None = None
) -> logging.Logger:
    """
    Obtiene o crea un logger configurado con las opciones del proyecto.

    Args:
        name: Nombre del logger. Si es None, usa APP_NAME.
        level: Nivel de logging. Si es None, usa LOGGER_LEVEL.
               Puede ser un string ("INFO", "WARNING", etc.) o un int (logging.INFO).

    Returns:
        Logger configurado y listo para usar.
    """
    logger_name = name or APP_NAME
    logger_level = level or LOGGER_LEVEL

    logger = logging.getLogger(logger_name)
    logger.setLevel(logger_level)
    logger.propagate = False  # Evita que se duplique en el logger raíz

    # Solo agregar handlers si no existen (evita duplicados)
    if not logger.hasHandlers():
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _apply_sensitive_filter()
    return logger
