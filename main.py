from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.environments import CORS_ORIGINS, DOCS_ENABLED, LOGGER_MIDDLEWARE_ENABLED
from app.exceptions import (
    AppHttpException,
    app_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from app.middleware.ContextMiddleware import ContextMiddleware
from app.middleware.LoggerMiddleware import LoggerMiddleware
from app.routes.routes import router as routes_router

app = FastAPI(
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)

# === Middlewares (orden: último en add_middleware = primero en ejecutarse)
if LOGGER_MIDDLEWARE_ENABLED:
    app.add_middleware(LoggerMiddleware)
app.add_middleware(ContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Exceptions
app.add_exception_handler(AppHttpException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# === Router
app.include_router(routes_router)
