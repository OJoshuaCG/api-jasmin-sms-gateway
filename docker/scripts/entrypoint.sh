#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Función: esperar a que MariaDB esté lista para conexiones
# Aunque el healthcheck de Docker Compose ya lo verifica, puede existir una
# pequeña ventana donde el usuario aún no tiene permisos. Reintentamos aquí.
# ─────────────────────────────────────────────────────────────────────────────
wait_for_db() {
    local max_retries=15
    local retry=0

    echo "[entrypoint] Esperando conexión a MariaDB (${DB_HOST}:${DB_PORT:-3306})..."

    until python - <<'PYEOF' 2>/dev/null
import pymysql, os, sys
try:
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        connect_timeout=3,
    )
    conn.close()
except Exception as e:
    print(f"  No disponible: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    do
        retry=$((retry + 1))
        if [ "$retry" -ge "$max_retries" ]; then
            echo "[entrypoint] ERROR: No se pudo conectar a MariaDB después de $max_retries intentos."
            exit 1
        fi
        echo "[entrypoint] MariaDB no lista (intento $retry/$max_retries). Reintentando en 3s..."
        sleep 3
    done

    echo "[entrypoint] Conexión a MariaDB establecida."
}

# ─────────────────────────────────────────────────────────────────────────────
# Función: aplicar migraciones Alembic
# ─────────────────────────────────────────────────────────────────────────────
run_migrations() {
    echo "[entrypoint] Aplicando migraciones Alembic..."
    alembic upgrade head
    echo "[entrypoint] Migraciones aplicadas correctamente."
}

# ─────────────────────────────────────────────────────────────────────────────
# Función: iniciar la aplicación FastAPI con Uvicorn
# WORKERS=1 por defecto. Con múltiples workers, configurar Redis para rate limiting.
# Ver: docs/features/rate-limiting.md
# ─────────────────────────────────────────────────────────────────────────────
start_app() {
    local workers="${WORKERS:-1}"
    echo "[entrypoint] Iniciando FastAPI con $workers worker(s)..."
    exec uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers "$workers" \
        --no-access-log \
        --proxy-headers \
        --forwarded-allow-ips "*"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
wait_for_db
run_migrations
start_app
