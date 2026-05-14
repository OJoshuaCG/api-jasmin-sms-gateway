import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent.parent
APP_DIR = ROOT_DIR / "app"

# ======= Application variables ======= #
APP_ENV = os.getenv("APP_ENV", "development")
APP_NAME = os.getenv("APP_NAME", "FastAPI Project")
SECRET_KEY = os.getenv("SECRET_KEY")


# ======= Logger variables ======= #
LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
LOGGER_MIDDLEWARE_ENABLED = (
    os.getenv("LOGGER_MIDDLEWARE_ENABLED", "True").lower() == "true"
)
LOGGER_MIDDLEWARE_SHOW_HEADERS = (
    os.getenv("LOGGER_MIDDLEWARE_SHOW_HEADERS", "False").lower() == "true"
)
LOGGER_MIDDLEWARE_SHOW_QUERY_PARAMS = (
    os.getenv("LOGGER_MIDDLEWARE_SHOW_QUERY_PARAMS", "True").lower() == "true"
)
LOGGER_MIDDLEWARE_SHOW_BODY = (
    os.getenv("LOGGER_MIDDLEWARE_SHOW_BODY", "True").lower() == "true"
)
LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS = (
    os.getenv("LOGGER_MIDDLEWARE_SHOW_PATH_PARAMS", "True").lower() == "true"
)
LOGGER_EXCEPTIONS_ENABLED = (
    os.getenv("LOGGER_EXCEPTIONS_ENABLED", "False").lower() == "true"
)
LOGGER_MIDDLEWARE_ERRORS_ONLY = (
    os.getenv("LOGGER_MIDDLEWARE_ERRORS_ONLY", "False").lower() == "true"
)

# ======= Docs variables ======= #
DOCS_ENABLED = os.getenv("DOCS_ENABLED", "True").lower() == "true"
DOCS_PASSWORD_ENABLED = os.getenv("DOCS_PASSWORD_ENABLED", "False").lower() == "true"
DOCS_USER = os.getenv("DOCS_USER", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "")

# ======= Rate limiting variables ======= #
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
RATE_LIMIT_REDIS_ENABLED = os.getenv("RATE_LIMIT_REDIS_ENABLED", "False").lower() == "true"
RATE_LIMIT_REDIS_URL = os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379")

# ======= Pagination variables ======= #
# Máximo de elementos por página. Hardcap en código: 200.
# Si PAGINATION_MAX_SIZE supera 200, se ignora y se usa 200.
PAGINATION_MAX_SIZE: int = min(int(os.getenv("PAGINATION_MAX_SIZE", "50")), 200)

# ======= Request size variables ======= #
REQUEST_MAX_SIZE_MB: float = float(os.getenv("REQUEST_MAX_SIZE_MB", "10"))

# ======= CORS variables ======= #
_cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()
]

# ======= Database variables ======= #
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "username")
DB_PASS = os.getenv("DB_PASS", "password")
DB_NAME = os.getenv("DB_NAME", "database")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")

# ======= Jasmin Telnet variables ======= #
JASMIN_TELNET_HOST = os.getenv("JASMIN_TELNET_HOST", "localhost")
JASMIN_TELNET_PORT = int(os.getenv("JASMIN_TELNET_PORT", "8990"))
JASMIN_TELNET_USER = os.getenv("JASMIN_TELNET_USER", "jcliadmin")
_JASMIN_TELNET_PASSWORD_RAW = os.getenv("JASMIN_TELNET_PASSWORD")
JASMIN_TELNET_PASSWORD = _JASMIN_TELNET_PASSWORD_RAW if _JASMIN_TELNET_PASSWORD_RAW is not None else "jclipwd"
JASMIN_TELNET_TIMEOUT = int(os.getenv("JASMIN_TELNET_TIMEOUT", "10"))

# ======= Jasmin HTTP API variables ======= #
JASMIN_HTTP_HOST = os.getenv("JASMIN_HTTP_HOST", "localhost")
JASMIN_HTTP_PORT = int(os.getenv("JASMIN_HTTP_PORT", "1401"))

# ======= Admin API variables ======= #
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
JASMIN_SCRIPTS_DIR = os.getenv("JASMIN_SCRIPTS_DIR", "/etc/jasmin/scripts")

# ======= Startup validation ======= #
import logging as _logging

if not SECRET_KEY:
    if APP_ENV == "production":
        raise ValueError(
            "SECRET_KEY no está definido. "
            "Establece la variable de entorno SECRET_KEY antes de iniciar en producción."
        )
    _logging.warning(
        "SECRET_KEY no está definido. Define SECRET_KEY en tu .env para evitar este aviso."
    )

if not ADMIN_API_KEY:
    if APP_ENV == "production":
        raise ValueError(
            "ADMIN_API_KEY no está definido. "
            'Genera una clave con: python -c "import secrets; print(secrets.token_urlsafe(32))" '
            "y establécela como variable de entorno ADMIN_API_KEY."
        )
    _logging.warning(
        "ADMIN_API_KEY no está definido. Todos los endpoints de la API devolverán 500. "
        "Define ADMIN_API_KEY en tu .env."
    )

if APP_ENV == "production":
    if _JASMIN_TELNET_PASSWORD_RAW is None:
        raise ValueError(
            "JASMIN_TELNET_PASSWORD no está definido. "
            "Define JASMIN_TELNET_PASSWORD en producción."
        )
    if CORS_ORIGINS == ["*"]:
        _logging.warning(
            "CORS_ORIGINS está configurado como '*' (permite cualquier origen). "
            "Considera restringirlo a los dominios autorizados en producción."
        )
