# Troubleshooting — Jasmin API Gateway

## Errores de inicio

### `ValueError: ADMIN_API_KEY no está definido`

**Causa:** `APP_ENV=production` pero `ADMIN_API_KEY` está vacío en el `.env`.

**Solución:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copia el resultado y agrégalo al .env:
ADMIN_API_KEY=<resultado>
```

---

### `ValueError: SECRET_KEY no está definido`

**Causa:** Igual que el anterior pero para `SECRET_KEY`.

**Solución:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Agregar al .env:
SECRET_KEY=<resultado>
```

---

### `ConnectionError: jcli authentication failed`

**Causa:** `JASMIN_TELNET_USER` o `JASMIN_TELNET_PASSWORD` incorrectos.

**Diagnóstico:**
```bash
# Verificar credenciales conectándose manualmente
telnet localhost 8990
# Username: jcliadmin
# Password: jclipwd
```

**Solución:** Revisar las credenciales del jcli en el archivo de configuración de Jasmin (`/etc/jasmin/jasmin.cfg`) y actualizar el `.env`.

---

### El gateway arranca pero responde `503` en todos los endpoints

**Causa:** No pudo conectar con Jasmin al iniciar (modo degradado). El gateway arranca igual pero marca todas las solicitudes como no disponibles.

**Verificar:**
```bash
# ¿Jasmin está corriendo?
systemctl status jasmin
# o
docker-compose ps

# ¿El puerto jcli está abierto?
nc -zv localhost 8990

# Ver logs del gateway
sudo journalctl -u jasmin-api-gateway -n 50
```

El gateway reintenta la conexión automáticamente con backoff exponencial (1s, 2s, 4s… máximo 30s). Una vez que Jasmin esté disponible, se reconecta solo.

**Forzar reconexión:**
```bash
curl -s -X POST http://localhost:8000/api/v1/system/reconnect \
  -H "X-API-Key: $KEY"
```

---

## Errores de autenticación

### `401 Unauthorized — Invalid or missing API key`

**Causa:** El header `X-API-Key` no fue enviado o no coincide con `ADMIN_API_KEY`.

**Verificar:**
```bash
# ¿Estás enviando el header?
curl -v -H "X-API-Key: tu-clave" http://localhost:8000/api/v1/groups/

# ¿La clave es exactamente la misma que en .env?
grep ADMIN_API_KEY /ruta/al/.env
```

---

### `500 — ADMIN_API_KEY is not configured on this server`

**Causa:** `ADMIN_API_KEY` está vacío en el `.env` y `APP_ENV=development` (en producción el servidor no arranca).

**Solución:** Definir `ADMIN_API_KEY` en el `.env` y reiniciar.

---

## Errores de Jasmin (jcli)

### `400 — Error: ...` en create/update

**Causa:** Jasmin rechazó el comando porque los datos son inválidos para su versión.

**Errores comunes:**

| Error de Jasmin | Causa probable | Solución |
|-----------------|----------------|----------|
| `Error: Unknown connector type` | Tipo de conector incorrecto | Verificar que `bind_to` es `transceiver`, `transmitter` o `receiver` |
| `Error: uid already taken` | Usuario con ese UID ya existe | Usar un UID diferente o verificar con `GET /users/{uid}` |
| `Error: gid not found` | El grupo asignado no existe | Crear el grupo primero con `POST /groups/` |
| `Error: connector already started` | El conector ya está activo | Verificar estado con `GET /smpp-connectors/{cid}/status` |
| `Error: connector already stopped` | El conector ya está detenido | Verificar estado antes de detener |
| `Error: Unknown route type` | Tipo de ruta inválido | Usar `DefaultRoute`, `StaticMTRoute`, `RandomRoundrobinMTRoute` o `LeastCostMTRoute` |
| `Error: Unknown filter id` | Filtro referenciado no existe | Crear el filtro primero con `POST /filters/` |

---

### `404 — User 'x' not found` justo después de crearlo

**Causa:** Jasmin no persiste la config a disco entre el create y el get. Raro, pero puede ocurrir si Jasmin está bajo carga.

**Verificar:**
```bash
# ¿Se guardó en Jasmin?
curl -H "X-API-Key: $KEY" http://localhost:8000/api/v1/system/session

# Forzar persist manual
curl -X POST -H "X-API-Key: $KEY" http://localhost:8000/api/v1/system/persist
```

---

### Los cambios se pierden al reiniciar Jasmin

**Causa:** La configuración se cambió pero no se persistió a disco.

El gateway llama `persist` automáticamente después de cada operación de escritura. Si ves que los cambios se pierden, verificar:

1. ¿El directorio de Jasmin tiene permisos de escritura?
   ```bash
   ls -la /etc/jasmin/
   ```

2. ¿Jasmin puede escribir su config?
   ```bash
   # Ver logs de Jasmin para errores de escritura
   tail -f /var/log/jasmin/jasmin.log
   ```

3. Persistir manualmente:
   ```bash
   curl -X POST -H "X-API-Key: $KEY" http://localhost:8000/api/v1/system/persist
   ```

---

## Errores de envío de SMS

### `422 — No route found for the message`

**Causa:** No hay ruta MT configurada para el usuario/destino.

**Solución:**
1. Verificar que existe una ruta MT: `GET /api/v1/mt-routes/`
2. Crear una ruta por defecto:
   ```bash
   curl -X POST -H "X-API-Key: $KEY" \
     -H "Content-Type: application/json" \
     -d '{"type":"DefaultRoute","order":0,"connectors":["tu_conector"]}' \
     http://localhost:8000/api/v1/mt-routes/
   ```

---

### `403 — Authentication failed or user quota exceeded`

**Causa:** Las credenciales del usuario SMS son incorrectas, el usuario está deshabilitado, o agotó su cuota/balance.

**Verificar:**
```bash
# Verificar estado del usuario
curl -H "X-API-Key: $KEY" http://localhost:8000/api/v1/users/nombre_usuario

# Verificar balance
curl -H "X-API-Key: $KEY" \
  "http://localhost:8000/api/v1/sms/balance?username=nombre_usuario&password=su_pass"
```

---

### `503 — Cannot reach Jasmin HTTP API`

**Causa:** El servicio HTTP de Jasmin (puerto 1401) no está disponible.

**Verificar:**
```bash
# ¿Jasmin HTTP API está corriendo?
curl -s http://localhost:1401/send?username=test&password=test&to=1&content=test
# Si responde algo (aunque sea error), está corriendo

# ¿El puerto está abierto?
nc -zv localhost 1401
```

---

## Errores de conectores SMPP

### El conector se conecta pero no envía mensajes

**Causa común:** `submit_throughput` configurado muy bajo, o el proveedor rechaza el bind.

**Verificar estado:**
```bash
curl -H "X-API-Key: $KEY" \
  http://localhost:8000/api/v1/smpp-connectors/tu_conector/status

# Ver estadísticas
curl -H "X-API-Key: $KEY" \
  http://localhost:8000/api/v1/stats/smpp-connectors/tu_conector
```

**Errores frecuentes en `last_error`:**

| Error | Causa |
|-------|-------|
| `BIND_FAILED` | Credenciales incorrectas en el proveedor |
| `CONNECTION_REFUSED` | Host/puerto del proveedor incorrecto |
| `THROTTLED` | El proveedor limita el throughput, bajar `submit_throughput` |
| `INVALID_PASSWORD` | Contraseña SMPP incorrecta (máximo 8 caracteres) |

---

## Problemas de rendimiento

### Las solicitudes tardan mucho

**Causa:** `GET /users/` y `GET /smpp-connectors/` hacen una llamada jcli por cada elemento (N+1). Con muchos usuarios/conectores, esto puede tardar varios segundos ya que jcli es serial.

**Estrategia:**
- Para listas grandes, usar `GET /users/{uid}` individual solo cuando sea necesario
- Configurar `JASMIN_TELNET_TIMEOUT` apropiado (default: 10s)
- Si el jcli tarda mucho en responder, verificar la carga del servidor Jasmin

---

### `asyncio.TimeoutError` en logs

**Causa:** Una operación jcli tardó más que `JASMIN_TELNET_TIMEOUT` segundos.

**Solución:** Aumentar el timeout si Jasmin está bajo carga:
```env
JASMIN_TELNET_TIMEOUT=30
```

---

## Herramientas de diagnóstico

```bash
# Estado general del servicio
sudo systemctl status jasmin-api-gateway

# Logs en tiempo real
sudo journalctl -u jasmin-api-gateway -f

# Últimas 100 líneas de log
sudo journalctl -u jasmin-api-gateway -n 100

# Health check del gateway
curl -s http://localhost:8000/health | python -m json.tool

# Estado de la sesión Telnet
curl -s -H "X-API-Key: $KEY" \
  http://localhost:8000/api/v1/system/session | python -m json.tool

# Verificar que Jasmin jcli responde
telnet localhost 8990

# Verificar que Jasmin HTTP API responde
curl -s "http://localhost:1401/send?username=x&password=x&to=1&content=x"

# Ver conexiones activas al gateway
sudo ss -tulpn | grep :8000

# Ver si el proceso gateway está corriendo
ps aux | grep uvicorn
```

---

## Logs útiles

### Ver solo errores

```bash
sudo journalctl -u jasmin-api-gateway -p err -f
```

### Filtrar por endpoint específico

```bash
sudo journalctl -u jasmin-api-gateway -f | grep "/smpp-connectors"
```

### En Docker

```bash
docker-compose logs -f jasmin-api-gateway
docker-compose logs --tail=100 jasmin-api-gateway
```
