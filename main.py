from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.environments import (
    JASMIN_HTTP_HOST,
    JASMIN_HTTP_PORT,
    JASMIN_TELNET_HOST,
    JASMIN_TELNET_PASSWORD,
    JASMIN_TELNET_PORT,
    JASMIN_TELNET_TIMEOUT,
    JASMIN_TELNET_USER,
)
from app.core.jasmin_http import close_jasmin_http_client, init_jasmin_http_client
from app.core.jasmin_telnet import JasminTelnetSession
from app.core.logger import get_logger
from app.core.versioned_app import create_versioned_app
from app.routes.health import router as health_router
from app.routes.v1.routes import router as v1_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────
    await init_jasmin_http_client(JASMIN_HTTP_HOST, JASMIN_HTTP_PORT)
    try:
        await JasminTelnetSession.init(
            host=JASMIN_TELNET_HOST,
            port=JASMIN_TELNET_PORT,
            user=JASMIN_TELNET_USER,
            password=JASMIN_TELNET_PASSWORD,
            timeout=JASMIN_TELNET_TIMEOUT,
        )
    except Exception as exc:
        logger.warning(
            "Could not connect to Jasmin jcli on startup: %s: %s. "
            "The API will start in degraded mode and retry automatically.",
            type(exc).__name__,
            exc,
        )
        # Still create the instance so get_instance() works; it will reconnect
        import asyncio as _asyncio
        session = JasminTelnetSession(
            JASMIN_TELNET_HOST,
            JASMIN_TELNET_PORT,
            JASMIN_TELNET_USER,
            JASMIN_TELNET_PASSWORD,
            JASMIN_TELNET_TIMEOUT,
        )
        JasminTelnetSession._instance = session
        _asyncio.create_task(session._reconnect_loop())

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    try:
        await JasminTelnetSession.get_instance().disconnect()
    except Exception:
        pass
    await close_jasmin_http_client()


# === Main app ────────────────────────────────────────────────────────
# Only manages unversioned routes (/health).
# Each versioned sub-app is self-contained with its own middleware stack.
app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.include_router(health_router)

# === API v1 ──────────────────────────────────────────────────────────
# Docs at /api/v1/docs and /api/v1/redoc
v1_app = create_versioned_app("v1")
v1_app.include_router(v1_router)
app.mount("/api/v1", v1_app)
