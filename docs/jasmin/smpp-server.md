# Servidor SMPP (`/smpp-server`)

## Qué es

El **SMPP Server** es el servidor SMPP integrado de Jasmin que permite que **clientes externos** (aplicaciones, sistemas de terceros) se conecten a Jasmin usando el protocolo SMPP para enviar mensajes MT.

A diferencia de los conectores SMPP salientes (`/smpp-connectors`), que conectan Jasmin hacia el carrier, el SMPP Server es el punto de entrada inbound: el sistema al que tus clientes se conectan como si Jasmin fuera el carrier.

```
Clientes externos (sistema UCaaS, plataforma propia)
    ↓  bind_transceiver / bind_transmitter
    SMPP Server de Jasmin (puerto 2775 por defecto)
    ↓  procesa como mensaje MT
    MT Interceptors → MT Routes → SMPP Connector → Carrier
```

---

## Lugar en el flujo

```
Cliente externo establece conexión SMPP
    → Jasmin SMPP Server autentica (usuario/contraseña configurados en /users)
    → Jasmin recibe submit_sm
    → Procesa igual que si viniera por HTTP: interceptores → rutas → carrier
```

Los usuarios que se conectan al SMPP Server son los mismos usuarios Jasmin gestionados en `/users`. La autorización se controla con `smpps_allow_bind` y `smpps_max_bindings` en el schema de usuario.

---

## Configuración

La configuración del SMPP Server **no puede modificarse via API**. Se gestiona en el archivo de configuración de Jasmin:

```
/etc/jasmin/jasmin.cfg → sección [smpp-server]
```

Los cambios en el archivo requieren reiniciar Jasmin para tener efecto.

### Parámetros en jasmin.cfg

```ini
[smpp-server]
# Interfaz de escucha (0.0.0.0 = todas las interfaces)
# bind = 0.0.0.0

# Puerto de escucha
# port = 2775

# Máximo de bindings simultáneos (0 = sin límite)
# max_bindings = 0
```

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/smpp-server/` | Lee la configuración actual desde jasmin.cfg |
| `PATCH` | `/smpp-server/` | **No soportado** — devuelve 501 |

> **Nota:** `PATCH /smpp-server/` siempre retorna 501 porque la configuración del SMPP Server requiere editar jasmin.cfg y reiniciar Jasmin.

---

## Respuesta (`SmppServerOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `host` | `string` | Interfaz de escucha (default: `"0.0.0.0"`) |
| `port` | `int` | Puerto SMPP (default: `2775`) |
| `max_bindings` | `int \| null` | Máximo de sesiones simultáneas. `null` = sin límite |

---

## Ejemplo

```bash
# Ver configuración actual
curl https://api.example.com/api/v1/smpp-server/ \
  -H "X-API-Key: tu-api-key"
```

Respuesta típica con configuración por defecto:

```json
{
  "data": {
    "host": "0.0.0.0",
    "port": 2775,
    "max_bindings": null
  }
}
```

---

## Gestión de usuarios SMPP

Para que un cliente pueda conectarse al SMPP Server, necesita un usuario Jasmin con los permisos correctos. Los campos relevantes al crear/actualizar un usuario (`POST /users/`):

| Campo | Default | Descripción |
|-------|---------|-------------|
| `smpps_allow_bind` | `true` | Permite al usuario hacer bind al SMPP Server |
| `smpps_max_bindings` | `null` (sin límite) | Máximo de sesiones simultáneas para este usuario |
| `smpps_quota_sms_count` | `null` (sin límite) | Cuota de SMS vía SMPP |
| `smpps_throughput` | `null` (sin límite) | Mensajes por segundo máximos vía SMPP |

Ejemplo — crear un usuario solo para uso SMPP:

```bash
curl -X POST https://api.example.com/api/v1/users/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "smpp_client_01",
    "gid": "smpp_clients",
    "username": "smpp_client_01",
    "password": "secure_password",
    "smpps_allow_bind": true,
    "smpps_max_bindings": 5,
    "smpps_throughput": 50.0
  }'
```

---

## Estadísticas del SMPP Server

Las métricas en tiempo real del SMPP Server están disponibles en:

```bash
GET /api/v1/stats/smpp-server-api
```

Incluye contadores de conexiones, binds, PDUs enviados/recibidos y errores. Ver documentación de [estadísticas](./stats.md).

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 500 | `Failed to read SMPP server configuration` | No se puede leer `/etc/jasmin/jasmin.cfg` |
| 501 | `SMPP server configuration cannot be updated via API` | Intento de usar PATCH (no soportado) |
