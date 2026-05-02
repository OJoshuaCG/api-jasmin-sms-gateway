# Guía de Despliegue — Jasmin API Gateway

Esta guía cubre cómo instalar y configurar el API Gateway sobre un servidor que ya tiene Jasmin SMS Gateway funcionando, ya sea instalado de forma nativa o en Docker.

---

## Requisitos previos

- Python 3.13+
- `uv` (gestor de paquetes)
- Jasmin SMS Gateway corriendo (nativo o Docker)
- Puerto 8990 (jcli Telnet) accesible desde el gateway
- Puerto 1401 (HTTP API de Jasmin) accesible desde el gateway

### Instalar `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env  # o reinicia la sesión
```

---

## Escenario A: Jasmin nativo en el mismo servidor

En este caso Jasmin está instalado directamente en el servidor (no Docker). El gateway se instala como servicio systemd en el mismo host.

### 1. Clonar y configurar

```bash
# Crear usuario dedicado (opcional pero recomendado)
sudo useradd -m -s /bin/bash jasmin-gw
sudo -u jasmin-gw bash

# Clonar el repositorio
cd /home/jasmin-gw
git clone <repo-url> api-gateway
cd api-gateway

# Instalar dependencias
uv sync --no-dev
```

### 2. Crear el archivo `.env`

```bash
cp .env.example .env
nano .env
```

Valores mínimos para producción:

```env
APP_ENV=production
APP_NAME="Jasmin API Gateway"
SECRET_KEY=<genera con: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_API_KEY=<genera con: python -c "import secrets; print(secrets.token_urlsafe(32))">

# Jasmin — mismo servidor, localhost siempre
JASMIN_TELNET_HOST=localhost
JASMIN_TELNET_PORT=8990
JASMIN_TELNET_USER=jcliadmin
JASMIN_TELNET_PASSWORD=<contraseña del jcli de Jasmin>
JASMIN_TELNET_TIMEOUT=10

JASMIN_HTTP_HOST=localhost
JASMIN_HTTP_PORT=1401

# Logging — solo errores en producción
LOGGER_LEVEL=WARNING
LOGGER_MIDDLEWARE_ENABLED=True
LOGGER_MIDDLEWARE_ERRORS_ONLY=True
LOGGER_MIDDLEWARE_SHOW_HEADERS=False
LOGGER_MIDDLEWARE_SHOW_BODY=False

# Documentación — desactivar o proteger en producción
DOCS_ENABLED=False

# Rate limiting
RATE_LIMIT_DEFAULT=60/minute

# Directorio de scripts de interceptores
JASMIN_SCRIPTS_DIR=/etc/jasmin/scripts
```

### 3. Verificar conexión con Jasmin

Antes de instalar el servicio, verifica que el gateway puede conectarse:

```bash
# Verificar puerto Telnet de Jasmin
telnet localhost 8990

# Verificar puerto HTTP de Jasmin
curl -s "http://localhost:1401/send?username=test&password=test&to=1234&content=test"
# Esperado: error de autenticación, no "connection refused"
```

### 4. Crear servicio systemd

Crear `/etc/systemd/system/jasmin-api-gateway.service`:

```ini
[Unit]
Description=Jasmin API Gateway
After=network.target jasmin.service
Wants=jasmin.service

[Service]
Type=simple
User=jasmin-gw
Group=jasmin-gw
WorkingDirectory=/home/jasmin-gw/api-gateway
EnvironmentFile=/home/jasmin-gw/api-gateway/.env
ExecStart=/home/jasmin-gw/.local/bin/uv run uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

# Seguridad
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

> **Nota:** `--host 127.0.0.1` — escucha solo en loopback. Nginx expone el puerto al exterior.

```bash
sudo systemctl daemon-reload
sudo systemctl enable jasmin-api-gateway
sudo systemctl start jasmin-api-gateway
sudo systemctl status jasmin-api-gateway
```

### 5. Nginx como reverse proxy

```bash
sudo apt install nginx -y
```

Crear `/etc/nginx/sites-available/jasmin-api-gateway`:

```nginx
server {
    listen 80;
    server_name api.tudominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.tudominio.com;

    ssl_certificate     /etc/letsencrypt/live/api.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.tudominio.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # No exponer versión de nginx
    server_tokens off;

    # Headers de seguridad
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        client_max_body_size 2M;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/jasmin-api-gateway /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL con Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.tudominio.com
```

### 6. Verificar instalación

```bash
# Health check (sin API key)
curl https://api.tudominio.com/health

# Listar grupos (con API key)
curl -H "X-API-Key: <tu-api-key>" https://api.tudominio.com/api/v1/groups/

# Ver logs
sudo journalctl -u jasmin-api-gateway -f
```

---

## Escenario B: Jasmin en Docker

En este caso Jasmin corre en Docker. El gateway se agrega al mismo `docker-compose.yml` como servicio adicional (sidecar).

### Opción B1: Agregar el gateway al docker-compose de Jasmin

Si ya tienes un `docker-compose.yml` con Jasmin, agrega el servicio del gateway:

```yaml
version: '3.8'

services:
  # ── Servicios existentes de Jasmin ──────────────────────────────
  jasmin:
    image: jookies/jasmin:latest
    ports:
      - "1401:1401"   # HTTP API (exponer si clientes externos lo necesitan)
      # NO exponer 8990 (jcli) al exterior
    volumes:
      - jasmin_config:/etc/jasmin
      - jasmin_logs:/var/log/jasmin
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  rabbit:
    image: rabbitmq:3-management-alpine
    restart: unless-stopped

  # ── API Gateway (nuevo) ─────────────────────────────────────────
  jasmin-api-gateway:
    build:
      context: ./jasmin-api-gateway   # ruta al repo del gateway
      dockerfile: Dockerfile
    env_file: ./jasmin-api-gateway/.env.production
    environment:
      # Apunta al servicio "jasmin" dentro de la red Docker
      JASMIN_TELNET_HOST: jasmin
      JASMIN_TELNET_PORT: "8990"
      JASMIN_HTTP_HOST: jasmin
      JASMIN_HTTP_PORT: "1401"
    ports:
      - "127.0.0.1:8000:8000"   # Solo loopback — Nginx lo expone
    depends_on:
      - jasmin
    restart: unless-stopped
    volumes:
      - jasmin_config:/etc/jasmin   # compartir directorio de scripts

volumes:
  jasmin_config:
  jasmin_logs:
```

### Dockerfile del gateway

Crea `Dockerfile` en la raíz del repositorio del gateway:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### Archivo `.env.production` para Docker

```env
APP_ENV=production
APP_NAME="Jasmin API Gateway"
SECRET_KEY=<clave-secreta>
ADMIN_API_KEY=<api-key-produccion>

# En Docker, los hosts se resuelven por nombre de servicio
JASMIN_TELNET_HOST=jasmin
JASMIN_TELNET_PORT=8990
JASMIN_TELNET_USER=jcliadmin
JASMIN_TELNET_PASSWORD=jclipwd
JASMIN_TELNET_TIMEOUT=10

JASMIN_HTTP_HOST=jasmin
JASMIN_HTTP_PORT=1401

LOGGER_LEVEL=WARNING
LOGGER_MIDDLEWARE_ENABLED=True
LOGGER_MIDDLEWARE_ERRORS_ONLY=True

DOCS_ENABLED=False
RATE_LIMIT_DEFAULT=60/minute

JASMIN_SCRIPTS_DIR=/etc/jasmin/scripts
```

### Construir y levantar

```bash
# Primera vez
docker-compose up -d --build

# Ver logs del gateway
docker-compose logs -f jasmin-api-gateway

# Verificar estado
docker-compose ps

# Reiniciar solo el gateway (sin afectar Jasmin)
docker-compose restart jasmin-api-gateway
```

### Opción B2: Gateway fuera de Docker (Jasmin en Docker)

Si prefieres no dockerizar el gateway:

```bash
# El gateway corre en el host, Jasmin en Docker
# Mapear el puerto jcli al host en el docker-compose de Jasmin:
#   ports:
#     - "127.0.0.1:8990:8990"   # jcli solo en loopback del host

# En el .env del gateway:
JASMIN_TELNET_HOST=127.0.0.1
JASMIN_TELNET_PORT=8990
JASMIN_HTTP_HOST=127.0.0.1
JASMIN_HTTP_PORT=1401
```

---

## Variables de entorno — Referencia completa

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `APP_ENV` | No | `development` | `production` activa validaciones estrictas |
| `APP_NAME` | No | `FastAPI Project` | Nombre en la documentación |
| `SECRET_KEY` | **Sí (prod)** | — | Clave interna. Genera: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_API_KEY` | **Sí (prod)** | — | Clave para `X-API-Key`. Genera: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `JASMIN_TELNET_HOST` | No | `localhost` | Host del jcli de Jasmin |
| `JASMIN_TELNET_PORT` | No | `8990` | Puerto del jcli |
| `JASMIN_TELNET_USER` | No | `jcliadmin` | Usuario jcli |
| `JASMIN_TELNET_PASSWORD` | No | `jclipwd` | Contraseña jcli |
| `JASMIN_TELNET_TIMEOUT` | No | `10` | Timeout (segundos) por comando jcli |
| `JASMIN_HTTP_HOST` | No | `localhost` | Host del HTTP API de Jasmin |
| `JASMIN_HTTP_PORT` | No | `1401` | Puerto del HTTP API |
| `JASMIN_SCRIPTS_DIR` | No | `/etc/jasmin/scripts` | Directorio para scripts de interceptores |
| `DOCS_ENABLED` | No | `True` | Habilitar `/docs` y `/redoc` |
| `DOCS_PASSWORD_ENABLED` | No | `False` | Proteger docs con HTTP Basic Auth |
| `DOCS_USER` | No | `admin` | Usuario para docs protegidas |
| `DOCS_PASSWORD` | No | — | Contraseña para docs protegidas |
| `LOGGER_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOGGER_MIDDLEWARE_ENABLED` | No | `True` | Loggear cada request/response |
| `LOGGER_MIDDLEWARE_ERRORS_ONLY` | No | `False` | Solo loggear errores (4xx/5xx) |
| `LOGGER_MIDDLEWARE_SHOW_HEADERS` | No | `False` | Incluir headers en logs (keys sensibles se redactan automáticamente) |
| `LOGGER_MIDDLEWARE_SHOW_BODY` | No | `True` | Incluir body en logs |
| `RATE_LIMIT_DEFAULT` | No | `100/minute` | Límite global por IP |
| `RATE_LIMIT_REDIS_ENABLED` | No | `False` | Usar Redis para contadores (multi-worker) |
| `RATE_LIMIT_REDIS_URL` | No | `redis://localhost:6379` | URI de Redis |
| `CORS_ORIGINS` | No | `*` | Orígenes permitidos, separados por coma |
| `REQUEST_MAX_SIZE_MB` | No | `10` | Tamaño máximo de request en MB |

---

## Actualizar el gateway

### Nativo (systemd)

```bash
cd /home/jasmin-gw/api-gateway
git pull
uv sync --no-dev
sudo systemctl restart jasmin-api-gateway
```

### Docker

```bash
git pull
docker-compose up -d --build jasmin-api-gateway
```

---

## Checklist de producción

- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` generada de forma segura
- [ ] `ADMIN_API_KEY` generada de forma segura y almacenada en bóveda de secretos
- [ ] `DOCS_ENABLED=False` (o protegida con contraseña)
- [ ] `LOGGER_MIDDLEWARE_SHOW_HEADERS=False`
- [ ] `LOGGER_MIDDLEWARE_SHOW_BODY=False`
- [ ] `CORS_ORIGINS` restringido a dominios conocidos (no `*`)
- [ ] Nginx configurado como reverse proxy
- [ ] HTTPS activo (certificado TLS)
- [ ] Puerto 8990 (jcli) NO expuesto al exterior
- [ ] Puerto 8000 (gateway) NO expuesto directamente (solo via Nginx)
- [ ] Servicio configurado para reiniciarse automáticamente
- [ ] Logs funcionando (`journalctl -u jasmin-api-gateway`)
- [ ] Health check respondiendo: `GET /health`
