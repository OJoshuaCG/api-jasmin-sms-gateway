# ─────────────────────────────────────────────────────────────────────────────
# Builder: instala dependencias con uv y genera el entorno virtual
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Copiar binario de uv desde la imagen oficial (más rápido que pip install uv)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Evitar que uv descargue Python (usamos el del sistema base)
# UV_LINK_MODE=copy es necesario en Docker (no hay hardlinks entre capas)
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Instalar dependencias primero (esta capa se cachea si pyproject.toml/uv.lock no cambian)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copiar el código fuente e instalar el proyecto
COPY . .
RUN uv sync --frozen --no-dev


# ─────────────────────────────────────────────────────────────────────────────
# Production: imagen final mínima y segura
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS production

# uv disponible en producción para comandos de entorno (alembic, etc.)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Dependencias de sistema mínimas (curl para el healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root para mayor seguridad
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copiar entorno virtual y código desde el builder (con ownership correcto)
COPY --from=builder --chown=appuser:appuser /app /app

# Hacer ejecutable el entrypoint (como root antes de cambiar de usuario)
RUN chmod +x /app/docker/scripts/entrypoint.sh

USER appuser

# Virtual env en PATH para ejecutar uvicorn/alembic directamente
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    UV_PYTHON_DOWNLOADS=0

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/docker/scripts/entrypoint.sh"]
