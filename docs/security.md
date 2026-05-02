# Seguridad — Jasmin API Gateway

## Modelo de seguridad

El gateway implementa autenticación por **API Key estática** via header HTTP. Toda solicitud a `/api/v1/*` debe incluir el header `X-API-Key` con la clave configurada en `ADMIN_API_KEY`.

```
Cliente → [HTTPS + X-API-Key] → Nginx → Gateway → Jasmin jcli (localhost)
```

El endpoint `/health` no requiere autenticación (es público para health checks de infraestructura).

---

## API Key

### Cómo funciona

- Cada request a `/api/v1/*` pasa por la dependencia `require_api_key`
- Si el header `X-API-Key` falta o no coincide con `ADMIN_API_KEY`: responde `401 Unauthorized`
- Si `ADMIN_API_KEY` no está configurado en el servidor: responde `500` (en producción, el servidor ni siquiera arranca)

### Generar una API Key segura

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Ejemplo: Kj3mN8xQpR5vL2wA9bT6uE1cF4hG7iJ0
```

Usa una clave de al menos 32 caracteres aleatorios. Nunca uses palabras, fechas, o valores predecibles.

### Configurar en el servidor

```bash
# En .env
ADMIN_API_KEY=Kj3mN8xQpR5vL2wA9bT6uE1cF4hG7iJ0
```

En producción, `APP_ENV=production` hace que el servidor **no arranque** si `ADMIN_API_KEY` está vacío.

### Incluirla en las solicitudes

```bash
# Header requerido en todos los endpoints de la API
curl -H "X-API-Key: Kj3mN8xQpR5vL2wA9bT6uE1cF4hG7iJ0" \
     https://api.tudominio.com/api/v1/groups/
```

### Rotar la API Key

Para rotar la clave sin downtime:

1. Genera una nueva clave: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Actualiza `ADMIN_API_KEY` en el `.env`
3. Notifica a los consumidores de la API
4. Reinicia el gateway: `sudo systemctl restart jasmin-api-gateway`
5. Los clientes deben actualizar su clave antes del reinicio

> El gateway no soporta múltiples claves activas simultáneamente. Si necesitas rotación sin downtime, usa Nginx para manejar el cambio de clave durante una ventana de transición.

---

## Capa de seguridad en profundidad

### 1. HTTPS (obligatorio en producción)

**Sin HTTPS, la API Key viaja en texto plano** — cualquiera en la red puede capturarla.

El `X-API-Key` en el header es seguro SOLO si la conexión usa TLS. Configurar Nginx con SSL (ver `docs/deployment.md`).

```nginx
# Nginx redirige HTTP → HTTPS automáticamente
server {
    listen 80;
    return 301 https://$server_name$request_uri;
}
```

### 2. Restringir CORS

En producción, no usar `CORS_ORIGINS=*`. Define solo los dominios que necesitan acceso:

```env
CORS_ORIGINS=https://panel.tudominio.com,https://admin.tudominio.com
```

### 3. Rate limiting

Configurado por IP via SlowAPI. Limita solicitudes masivas o ataques de fuerza bruta:

```env
RATE_LIMIT_DEFAULT=60/minute
```

Si el gateway tiene múltiples workers o réplicas, usa Redis para compartir los contadores:

```env
RATE_LIMIT_REDIS_ENABLED=True
RATE_LIMIT_REDIS_URL=redis://localhost:6379
```

### 4. No exponer puertos internos de Jasmin

El jcli (puerto 8990) y el HTTP API de Jasmin (puerto 1401) **NO deben estar accesibles desde el exterior**. Solo el gateway debe comunicarse con ellos.

**Verificar con `ufw` (Ubuntu):**

```bash
# Solo exponer 80 y 443 (Nginx)
sudo ufw allow 80
sudo ufw allow 443
sudo ufw deny 8990
sudo ufw deny 1401
sudo ufw deny 8000
sudo ufw enable
```

**En Docker**, no mapear los puertos de Jasmin al exterior:

```yaml
# ✅ Correcto — puerto solo en red interna Docker
jasmin:
  image: jookies/jasmin:latest
  # NO poner ports: aquí si no necesitas acceso externo

# ❌ Incorrecto — expone jcli al mundo
jasmin:
  ports:
    - "8990:8990"
```

### 5. Proteger la documentación

En producción, desactiva la documentación o protégela:

```env
# Opción A: desactivar completamente
DOCS_ENABLED=False

# Opción B: proteger con contraseña HTTP Basic
DOCS_ENABLED=True
DOCS_PASSWORD_ENABLED=True
DOCS_USER=admin
DOCS_PASSWORD=<contraseña-segura>
```

### 6. Logs y datos sensibles

El logger redacta automáticamente estos headers si `LOGGER_MIDDLEWARE_SHOW_HEADERS=True`:
- `x-api-key` → `***`
- `authorization` → `***`
- `cookie` → `***`
- `set-cookie` → `***`

En producción, desactiva el body logging para evitar que contraseñas de SMS (username/password en `/sms/send`) aparezcan en logs:

```env
LOGGER_MIDDLEWARE_SHOW_BODY=False
LOGGER_MIDDLEWARE_SHOW_HEADERS=False
LOGGER_MIDDLEWARE_ERRORS_ONLY=True
```

### 7. Restricción por IP (opcional, recomendado si el acceso es fijo)

Si el gateway solo debe ser accesible desde IPs conocidas (ej. solo desde el servidor de tu aplicación), configura Nginx:

```nginx
server {
    listen 443 ssl http2;
    # ...

    location /api/ {
        # Permitir solo IPs conocidas
        allow 203.0.113.10;   # IP de tu servidor de aplicación
        allow 198.51.100.0/24; # Rango de tu oficina
        deny all;

        proxy_pass http://127.0.0.1:8000;
        # ...
    }
}
```

---

## Resumen de capas de seguridad

| Capa | Estado | Configuración |
|------|--------|---------------|
| **API Key (X-API-Key)** | ✅ Implementado | `ADMIN_API_KEY` en `.env` |
| **HTTPS/TLS** | Requiere Nginx | Certificado Let's Encrypt |
| **Rate limiting** | ✅ Implementado | `RATE_LIMIT_DEFAULT` |
| **CORS restringido** | Configurar | `CORS_ORIGINS=https://tudominio.com` |
| **Logs sin datos sensibles** | ✅ Automático (redacción) | `LOGGER_MIDDLEWARE_SHOW_HEADERS=False` |
| **Firewall (jcli/1401 cerrados)** | Configurar en SO | `ufw deny 8990` |
| **Documentación protegida** | Configurar | `DOCS_ENABLED=False` |
| **Restricción por IP** | Opcional | Regla `allow/deny` en Nginx |

---

## Qué NO implementa (y por qué)

- **JWT / OAuth2**: El gateway es una herramienta administrativa interna (sidecar). La autenticación por API Key estática es el estándar para APIs de administración interna. JWT sería overhead innecesario para un cliente de confianza.
- **Múltiples usuarios/roles**: Jasmin ya gestiona usuarios con permisos a nivel de mensajería. El gateway es para administradores del sistema.
- **Auditoría por usuario**: Todos los cambios se hacen con la misma API Key. Si necesitas auditoría, implementa un proxy de logging antes del gateway.
