# Jasmin SMS Gateway Admin API — Referencia Completa

**Base URL:** `http://<host>:8080`
**Versión actual:** `v1` (prefijo `/api/v1`)
**Formato:** JSON (`application/json`)
**Autenticación:** Header `X-API-Key` para administración · credenciales Jasmin para envío

> Este documento describe **todos** los endpoints disponibles, sus parámetros, los tipos de datos aceptados y los valores válidos para cada campo. Cada endpoint incluye al menos un ejemplo concreto de solicitud y respuesta.

---

## Tabla de contenidos

1. [Convenciones generales](#convenciones-generales)
   - [Autenticación](#autenticación)
   - [Formato de respuestas](#formato-de-respuestas)
   - [Códigos HTTP](#códigos-http)
   - [Tipos de datos y formatos comunes](#tipos-de-datos-y-formatos-comunes)
2. [Health](#health)
3. [Groups — Grupos](#groups--grupos)
4. [Users — Usuarios](#users--usuarios)
5. [SMPP Connectors](#smpp-connectors)
6. [HTTP Connectors](#http-connectors)
7. [Filters — Filtros](#filters--filtros)
8. [MT Routes — Rutas salientes](#mt-routes--rutas-salientes)
9. [MO Routes — Rutas entrantes](#mo-routes--rutas-entrantes)
10. [MT Interceptors](#mt-interceptors)
11. [MO Interceptors](#mo-interceptors)
12. [SMPP Server](#smpp-server)
13. [SMS — Envío y consultas](#sms--envío-y-consultas)
14. [Stats — Estadísticas](#stats--estadísticas)
15. [Insights — Vistas agregadas](#insights--vistas-agregadas)
16. [System — Mantenimiento](#system--mantenimiento)
17. [Notas de integración](#notas-de-integración)

---

## Convenciones generales

### Autenticación

| Tipo de endpoint | Mecanismo | Header / Parámetro |
|------------------|-----------|--------------------|
| Administración (`/api/v1/*` excepto `sms/*`) | API Key del sidecar | `X-API-Key: <tu-api-key>` |
| Envío de SMS (`/api/v1/sms/*`) | Credenciales del usuario Jasmin | `username` y `password` en el cuerpo o query string |
| `GET /health` | Sin autenticación | — |

Si la `X-API-Key` está ausente o es incorrecta, la respuesta es `401 Unauthorized`.

### Formato de respuestas

**Éxito (con datos):**
```json
{
  "data": { "uid": "user_mx_01", "enabled": true },
  "message": "User created"
}
```

**Éxito (sin datos, eg. DELETE):**
```json
{ "data": null, "message": "Group deleted" }
```

- `data` — objeto o array con la información solicitada. `null` en DELETE/acciones.
- `message` — presente sólo en operaciones de escritura (POST/PATCH/DELETE). En GET no aparece.
- Los campos `null` se omiten automáticamente del JSON de salida.

**Error estándar:**
```json
{
  "detail": {
    "msg": "Group 'premium_customers' already exists",
    "type": "AppHttpException"
  }
}
```

**Error 409 (recurso duplicado)** — incluye `existing` con el recurso conflictante:
```json
{
  "detail": {
    "msg": "Connector 'carrier_mx' already exists",
    "type": "AppHttpException",
    "existing": {
      "cid": "carrier_mx",
      "host": "smpp.carrier.com",
      "port": 2775,
      "username": "jasmin_prod",
      "bind_to": "transceiver"
    }
  }
}
```

**Error 422 (validación)** — formato estándar de FastAPI:
```json
{
  "detail": [
    {
      "loc": ["body", "port"],
      "msg": "Input should be less than or equal to 65535",
      "type": "less_than_equal"
    }
  ]
}
```

### Códigos HTTP

| Código | Significado |
|--------|-------------|
| `200` | OK — GET / PATCH exitoso |
| `201` | Created — POST exitoso |
| `400` | Bad Request — comando jcli rechazado, balance insuficiente, sin ruta, script eliminado en disco |
| `401` | Unauthorized — `X-API-Key` inválida o credenciales Jasmin inválidas |
| `404` | Not Found — el recurso no existe |
| `409` | Conflict — recurso duplicado (`detail.existing` con el recurso actual) |
| `412` | Precondition Failed — sin ruta válida para el destino solicitado |
| `422` | Unprocessable Entity — validación de tipo, longitud, regex, etc. |
| `503` | Service Unavailable — Jasmin no disponible (sesión Telnet caída o Jasmin caído) |

### Tipos de datos y formatos comunes

| Tipo lógico | Definición | Ejemplo válido |
|-------------|------------|----------------|
| `Identifier` | `string` 1–64 chars · regex `^[a-zA-Z0-9_-]+$` (sin espacios) | `user_mx_01`, `carrier-mx`, `ft_premium` |
| `Username Jasmin` | `string` sin espacios ni caracteres de control | `smpp_mx01` |
| `Password Jasmin` | `string` sin caracteres de control | `Secr3t!2024` |
| `MSISDN` | `string` E.164 recomendado (`+` opcional, dígitos) | `+525512345678`, `52155512345`, `25471234567` |
| `Sender ID alfanumérico` | `string` 1–11 chars (depende del carrier) | `MiTienda`, `InfoMX` |
| `Regex` | `string` con sintaxis regex de Python | `^254`, `^\+?52\d{10}$` |
| `Hex content` | `string` hexadecimal sin espacios (par de chars por byte) | `48656c6c6f` |
| `DateInterval` | `string` `"YYYY-MM-DD;YYYY-MM-DD"` | `"2024-01-01;2024-12-31"` |
| `TimeInterval` | `string` `"HH:MM:SS;HH:MM:SS"` (24h) | `"08:00:00;18:00:00"` |
| `Schedule / Validity` | `string` formato SMPP `YYMMDDHHmmss000R` (relative) o `YYMMDDHHmmss000+` | `"000000010000000R"` (+1h) |
| `Connector ID en rutas` | `smppc(<cid>)` · `http(<cid>)` · `smpps(<cid>)` | `smppc(carrier_mx)`, `http(webhook_crm)` |
| `Filter FID` | Identifier · referencia un filtro existente | `ft_premium`, `ft_src_mx` |
| `TON SMPP` | `integer` 0–6 | 0=Unknown, 1=Intl, 2=Nat, 5=Alphanumeric |
| `NPI SMPP` | `integer` 0–18 | 0=Unknown, 1=ISDN/E.164 |
| `Data coding` | `integer` 0–255 | 0=GSM7, 1=IA5/ASCII/Binary, 3=Latin-1, 8=UCS-2 |
| `DLR level` | `integer` 1, 2, 3 | 1=final, 2=intermedio, 3=ambos |

---

## Health

### `GET /health`

Verifica el estado del sidecar y la conectividad hacia Jasmin. **No requiere autenticación** y se sirve fuera del prefijo `/api/v1`.

**Response 200:**
```json
{
  "status": "ok",
  "service": "jasmin-admin-api",
  "environment": "production",
  "telnet": {
    "connected": true,
    "uptime_seconds": 3621.7,
    "reconnecting": false
  },
  "jasmin_http": { "reachable": true }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | `"ok"` \| `"error"` | Estado global del sidecar |
| `service` | string | Nombre del servicio (`APP_NAME`) |
| `environment` | string | `development` o `production` (`APP_ENV`) |
| `telnet.connected` | boolean | `true` si la sesión jcli está activa |
| `telnet.uptime_seconds` | float \| null | Segundos de la sesión actual |
| `telnet.reconnecting` | boolean | `true` si hay reconexión en curso |
| `jasmin_http.reachable` | boolean | `true` si el HTTP API de Jasmin responde |

> Siempre retorna 200 (degradado si Jasmin está caído).

---

## Groups — Grupos

Los grupos son contenedores de permisos. Cada usuario pertenece a exactamente un grupo. Deshabilitar un grupo bloquea de inmediato a todos sus usuarios.

### `GET /api/v1/groups/`

Lista todos los grupos.

**Response 200:**
```json
{
  "data": [
    { "gid": "premium_customers", "enabled": true },
    { "gid": "resellers",          "enabled": true },
    { "gid": "blocked_group",      "enabled": false }
  ]
}
```

**Errores:** `503`.

---

### `GET /api/v1/groups/{gid}`

Retorna un grupo por su ID.

**Path:**

| Parámetro | Tipo | Restricciones | Ejemplo |
|-----------|------|---------------|---------|
| `gid` | Identifier | 1–64 chars · `[a-zA-Z0-9_-]` | `premium_customers` |

**Response 200:**
```json
{ "data": { "gid": "premium_customers", "enabled": true } }
```

**Errores:** `404` · `503`.

---

### `POST /api/v1/groups/`

Crea un grupo nuevo.

**Body:**

| Campo | Tipo | Requerido | Restricciones | Ejemplo |
|-------|------|-----------|---------------|---------|
| `gid` | string | Sí | 1–64 chars · `[a-zA-Z0-9_-]` | `"premium_customers"` |

**Ejemplo de solicitud:**
```json
{ "gid": "premium_customers" }
```

**Response 201:**
```json
{
  "data": { "gid": "premium_customers", "enabled": true },
  "message": "Group created"
}
```

**Errores:**

- `409` — grupo ya existe (incluye `existing`).
- `422` — `gid` vacío, demasiado largo, o caracteres inválidos.
- `503` — Jasmin no disponible.

---

### `PATCH /api/v1/groups/{gid}`

Habilita o deshabilita un grupo.

**Body:**

| Campo | Tipo | Requerido | Valores aceptados | Descripción |
|-------|------|-----------|-------------------|-------------|
| `enabled` | boolean | Sí | `true` \| `false` | `false` bloquea a todos los usuarios del grupo |

**Ejemplo:**
```json
{ "enabled": false }
```

**Response 200:**
```json
{ "data": { "gid": "premium_customers", "enabled": false } }
```

**Errores:** `404` · `422` · `503`.

---

### `DELETE /api/v1/groups/{gid}`

Elimina un grupo.

> Eliminar un grupo con usuarios activos deja a esos usuarios sin grupo válido. Reasignar o eliminar usuarios primero.

**Response 200:**
```json
{ "data": null, "message": "Group deleted" }
```

**Errores:** `404` · `503`.

---

## Users — Usuarios

Los usuarios autentican para envío de SMS via HTTP API o bind SMPP. Cada usuario tiene cuotas, throughput, flags de autorización y filtros de valor.

### `GET /api/v1/users/`

Lista todos los usuarios.

**Response 200:**
```json
{
  "data": [
    {
      "uid": "user_mx_01",
      "gid": "premium_customers",
      "username": "smpp_mx01",
      "enabled": true,
      "balance": 150.0,
      "sms_count": null,
      "mt_throughput": 10.0,
      "smpps_throughput": null,
      "mt_auth_http_send": true,
      "mt_auth_http_balance": true,
      "mt_auth_http_rate": true,
      "mt_auth_http_bulk": false,
      "mt_auth_smpps_send": true,
      "mt_auth_long_content": true,
      "mt_auth_dlr_level": true,
      "mt_auth_http_dlr_method": true,
      "mt_auth_src_addr": true,
      "mt_auth_priority": true,
      "mt_auth_validity_period": true,
      "mt_auth_schedule_at": true,
      "mt_auth_hex_content": true,
      "mt_filter_src_addr": null,
      "mt_filter_dst_addr": null,
      "mt_filter_content": null,
      "mt_filter_priority": null,
      "mt_filter_validity_period": null,
      "mt_default_src_addr": null,
      "smpps_allow_bind": true,
      "smpps_max_bindings": null
    }
  ]
}
```

**Errores:** `503`.

---

### `GET /api/v1/users/{uid}`

Retorna un usuario por UID.

**Path:** `uid` (Identifier, 1–64 chars).

**Response 200:** misma estructura que un elemento del listado.

**Errores:** `404` · `503`.

---

### `POST /api/v1/users/`

Crea un usuario Jasmin nuevo.

**Body — campos requeridos:**

| Campo | Tipo | Restricciones | Ejemplo |
|-------|------|---------------|---------|
| `uid` | string | 1–64 chars · `[a-zA-Z0-9_-]` · debe ser único | `"user_mx_01"` |
| `gid` | string | 1–64 chars · `[a-zA-Z0-9_-]` · grupo debe existir | `"premium_customers"` |
| `username` | string | 1–64 chars · sin espacios, sin caracteres de control | `"smpp_mx01"` |
| `password` | string | ≥ 1 char · sin caracteres de control | `"Secr3t!2024"` |

**Body — campos opcionales (cuota y billing):**

| Campo | Tipo | Default | Valor `null` significa | Ejemplo |
|-------|------|---------|------------------------|---------|
| `balance` | float \| null | `null` | ilimitado | `200.0` |
| `sms_count` | int \| null | `null` | ilimitado | `5000` |
| `mt_quota_early_percent` | float \| null | `null` | sin aviso temprano | `10.0` |
| `mt_throughput` | float \| null | `null` | ilimitado | `20.0` |
| `smpps_throughput` | float \| null | `null` | ilimitado | `10.0` |

**Body — flags de autorización (booleans, default según Jasmin):**

| Campo | Default | Descripción |
|-------|---------|-------------|
| `mt_auth_http_send` | `true` | Permite enviar por HTTP API |
| `mt_auth_http_balance` | `true` | Permite consultar balance |
| `mt_auth_http_rate` | `true` | Permite consultar tarifa |
| `mt_auth_http_bulk` | `false` | Permite envío masivo HTTP |
| `mt_auth_smpps_send` | `true` | Permite enviar por SMPP server |
| `mt_auth_long_content` | `true` | Permite SMS largo (multipart) |
| `mt_auth_dlr_level` | `true` | Permite seleccionar nivel DLR |
| `mt_auth_http_dlr_method` | `true` | Permite método HTTP del DLR |
| `mt_auth_src_addr` | `true` | Permite personalizar sender ID |
| `mt_auth_priority` | `true` | Permite prioridad |
| `mt_auth_validity_period` | `true` | Permite validity period |
| `mt_auth_schedule_at` | `true` | Permite envío programado |
| `mt_auth_hex_content` | `true` | Permite contenido hex |

**Body — filtros de valor (regex, opcionales):**

| Campo | Tipo | Ejemplo | Cuándo aplicar |
|-------|------|---------|----------------|
| `mt_filter_src_addr` | regex \| null | `"^InfoMX$"` | El sender debe matchear esta regex |
| `mt_filter_dst_addr` | regex \| null | `"^\\+?52\\d{10}$"` | El destino debe matchear |
| `mt_filter_content` | regex \| null | `"^[A-Za-z0-9 ]+$"` | El texto debe matchear |
| `mt_filter_priority` | regex \| null | `"^[0-3]$"` | El valor de prioridad debe matchear |
| `mt_filter_validity_period` | regex \| null | `"^\\d+$"` | El validity period debe matchear |

**Body — defaults y SMPP server:**

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `mt_default_src_addr` | string \| null | `null` | Sender ID por defecto si el cliente no manda uno |
| `smpps_allow_bind` | boolean | `true` | Permite bind SMPP inbound |
| `smpps_max_bindings` | int \| null | `null` | Máx. binds SMPP simultáneos · `null` = ilimitado |

**Ejemplo mínimo:**
```json
{
  "uid": "user_mx_01",
  "gid": "premium_customers",
  "username": "smpp_mx01",
  "password": "Secr3t!2024"
}
```

**Ejemplo completo (prepago, México, restringido):**
```json
{
  "uid": "user_mx_01",
  "gid": "premium_customers",
  "username": "smpp_mx01",
  "password": "Secr3t!2024",
  "balance": 200.0,
  "sms_count": 5000,
  "mt_quota_early_percent": 10.0,
  "mt_throughput": 20.0,
  "smpps_throughput": 10.0,
  "mt_auth_http_send": true,
  "mt_auth_http_bulk": false,
  "mt_auth_src_addr": true,
  "mt_filter_dst_addr": "^\\+?52\\d{10}$",
  "mt_default_src_addr": "InfoMX",
  "smpps_allow_bind": true,
  "smpps_max_bindings": 2
}
```

**Response 201:** objeto `UserOut` completo (mismos campos que en la lista).

**Errores:**

- `404` — el `gid` referenciado no existe.
- `409` — usuario ya existe (incluye `existing`).
- `422` — validación de tipo, longitud, regex inválida.
- `503` — Jasmin no disponible.

---

### `PATCH /api/v1/users/{uid}`

Actualiza campos de un usuario. **Sólo los campos enviados se modifican.**

**Path:** `uid` (Identifier).

**Body:** cualquier subconjunto de los campos de `UserCreate` excepto `uid`. Para volver un valor a "ilimitado" envía `null` explícitamente:

```json
{ "balance": null, "sms_count": null }
```

**Ejemplo — cambiar grupo y subir throughput:**
```json
{ "gid": "resellers", "mt_throughput": 30.0 }
```

**Ejemplo — rotar contraseña:**
```json
{ "password": "NuevoPass#2024" }
```

**Ejemplo — sólo SMS a México con un sender fijo:**
```json
{
  "mt_filter_dst_addr": "^\\+?52\\d{10}$",
  "mt_default_src_addr": "InfoMX",
  "mt_auth_src_addr": false
}
```

**Response 200:** objeto `UserOut` completo actualizado.

**Errores:** `404` · `422` · `503`.

---

### `PATCH /api/v1/users/{uid}/status`

Habilita o deshabilita un usuario sin modificar el resto de su configuración.

**Body:**

| Campo | Tipo | Requerido | Valores | Descripción |
|-------|------|-----------|---------|-------------|
| `enabled` | boolean | Sí | `true` \| `false` | `false` bloquea inmediatamente HTTP y SMPP |

**Ejemplo:**
```json
{ "enabled": false }
```

**Response 200:** objeto `UserOut` con el nuevo estado.

**Errores:** `404` · `422` · `503`.

---

### `DELETE /api/v1/users/{uid}`

Elimina un usuario.

**Response 200:**
```json
{ "data": null, "message": "User deleted" }
```

**Errores:** `404` · `503`.

---

## SMPP Connectors

Los conectores SMPP outbound representan conexiones desde Jasmin hacia un SMSC (carrier/agregador). Después de crear un conector, **iniciarlo** con `POST /{cid}/start` para abrir la sesión.

### `GET /api/v1/smpp-connectors/`

Lista todos los conectores SMPP outbound.

**Response 200:**
```json
{
  "data": [
    {
      "cid": "carrier_mx",
      "host": "smpp.carrier.com",
      "port": 2775,
      "username": "jasmin_prod",
      "bind_to": "transceiver",
      "system_type": null,
      "address_range": null,
      "source_addr_ton": 1,
      "source_addr_npi": 1,
      "dest_addr_ton": 1,
      "dest_addr_npi": 1,
      "submit_throughput": 50.0,
      "dlr_expiry": 86400,
      "reconnect_on_connection_loss": true,
      "reconnect_on_connection_loss_delay": 10,
      "reconnect_on_connection_failure": true,
      "reconnect_on_connection_failure_delay": 10,
      "bind_timeout": null,
      "elink_interval": 30,
      "res_to": null,
      "pdu_red_to": null,
      "trx_to": null,
      "requeue_delay": null,
      "coding": 0,
      "dlr_msgid": 0,
      "ssl": false
    }
  ]
}
```

**Errores:** `503`.

---

### `GET /api/v1/smpp-connectors/{cid}`

Retorna un conector por su ID.

**Path:** `cid` (Identifier).

**Response 200:** objeto `SmppConnectorOut` (misma estructura que en la lista).

**Errores:** `404` · `503`.

---

### `POST /api/v1/smpp-connectors/`

Crea un nuevo conector SMPP outbound. Se crea **stopped**; iniciar con `POST /{cid}/start`.

**Body — campos requeridos:**

| Campo | Tipo | Restricciones | Ejemplo |
|-------|------|---------------|---------|
| `cid` | string | 1–64 chars · `[a-zA-Z0-9_-]` | `"carrier_mx"` |
| `host` | string | hostname o IP | `"smpp.carrier.com"` |
| `port` | int | 1–65535 | `2775` |
| `username` | string | 1–15 chars (límite SMPP 3.4) | `"jasmin_prod"` |
| `password` | string | 1–8 chars (límite SMPP 3.4) | `"Smpp@24"` |

**Body — bind y direccionamiento (todos opcionales):**

| Campo | Tipo | Valores válidos | Default | Descripción |
|-------|------|-----------------|---------|-------------|
| `bind_to` | enum | `"transceiver"` \| `"transmitter"` \| `"receiver"` | `"transceiver"` | Tipo de bind SMPP |
| `system_type` | string \| null | máx 12 chars | `null` | Campo `system_type` del bind |
| `address_range` | string \| null | máx 40 chars | `null` | Campo `address_range` del bind |
| `source_addr_ton` | int \| null | 0–6 | Jasmin default | TON origen |
| `source_addr_npi` | int \| null | 0–18 | Jasmin default | NPI origen |
| `dest_addr_ton` | int \| null | 0–6 | Jasmin default | TON destino |
| `dest_addr_npi` | int \| null | 0–18 | Jasmin default | NPI destino |

**Valores TON/NPI comunes:**

| TON | Significado | NPI | Significado |
|-----|-------------|-----|-------------|
| 0 | Unknown | 0 | Unknown |
| 1 | International (recomendado MSISDN) | 1 | ISDN/E.164 (recomendado MSISDN) |
| 2 | National | 3 | Data |
| 5 | Alphanumeric (sender ID) | 9 | Private |

**Body — throughput, DLR y reconexión:**

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `submit_throughput` | float ≥ 0 \| null | `null` (ilimitado) | Máx submit_sm/seg al SMSC |
| `dlr_expiry` | int ≥ 0 \| null | Jasmin default | Segundos antes de expirar DLR. Ej: `86400` (24h) |
| `reconnect_on_connection_loss` | boolean | `true` | Reconectar al perder sesión |
| `reconnect_on_connection_loss_delay` | int | `10` | Segundos antes de reconectar |
| `reconnect_on_connection_failure` | boolean | `true` | Reintentar al fallar conexión inicial |
| `reconnect_on_connection_failure_delay` | int | `10` | Segundos antes de reintentar |

**Body — timeouts (opcionales, segundos):**

| Campo | Default Jasmin | Descripción |
|-------|----------------|-------------|
| `bind_timeout` | `30` | Timeout del bind |
| `elink_interval` | `30` | Intervalo enquire-link keepalive |
| `res_to` | `120` | Response timeout |
| `pdu_red_to` | `10` | PDU inactivity redirect timeout |
| `trx_to` | `300` | TRX session inactivity timeout |
| `requeue_delay` | `120` | Espera antes de reintentar mensaje fallido |

**Body — encoding y TLS:**

| Campo | Tipo | Valores | Default | Descripción |
|-------|------|---------|---------|-------------|
| `coding` | int | 0–255 | `0` | `0`=GSM7, `1`=IA5/ASCII, `3`=Latin-1, `8`=UCS-2 |
| `dlr_msgid` | int | 0–2 | `0` | Campo PDU con el msgid en DLR: `0`=smpp msgid, `1`=receipted_msgid |
| `ssl` | boolean | `true`/`false` | `false` | Habilita TLS |

**Ejemplo mínimo:**
```json
{
  "cid": "carrier_mx",
  "host": "smpp.carrier.com",
  "port": 2775,
  "username": "jasmin_prod",
  "password": "Smpp@24"
}
```

**Ejemplo carrier internacional (transceiver con throughput limitado):**
```json
{
  "cid": "carrier_mx",
  "host": "smpp.carrier.com",
  "port": 2775,
  "username": "jasmin_prod",
  "password": "Smpp@24",
  "bind_to": "transceiver",
  "source_addr_ton": 5,
  "source_addr_npi": 0,
  "dest_addr_ton": 1,
  "dest_addr_npi": 1,
  "submit_throughput": 50.0,
  "dlr_expiry": 86400,
  "elink_interval": 30,
  "coding": 0,
  "ssl": false
}
```

**Ejemplo carrier con TLS:**
```json
{
  "cid": "carrier_secure",
  "host": "smpps.carrier.com",
  "port": 3550,
  "username": "secure_user",
  "password": "Smpp@99",
  "bind_to": "transceiver",
  "ssl": true,
  "submit_throughput": 100.0
}
```

**Response 201:**
```json
{
  "data": { "cid": "carrier_mx", "host": "smpp.carrier.com", "port": 2775, "...": "..." },
  "message": "Connector created"
}
```

**Errores:** `409` (con `existing`) · `422` · `503`.

---

### `PATCH /api/v1/smpp-connectors/{cid}`

Actualiza campos de un conector. **Detener el conector antes de actualizar** (`POST /{cid}/stop`).

**Path:** `cid` (Identifier).

**Body:** cualquier subconjunto de los campos opcionales de `SmppConnectorCreate` (no se puede cambiar el `cid`).

**Ejemplo — cambiar host y subir throughput:**
```json
{ "host": "smpp2.carrier.com", "submit_throughput": 100.0 }
```

**Ejemplo — rotar credenciales:**
```json
{ "username": "new_user", "password": "NewSmpp1" }
```

**Response 200:** `SmppConnectorOut` actualizado.

**Errores:** `404` · `422` · `503`.

---

### `DELETE /api/v1/smpp-connectors/{cid}`

Elimina un conector SMPP. Detenerlo y quitar referencias en rutas MT antes de eliminar.

**Response 200:**
```json
{ "data": null, "message": "Connector deleted" }
```

**Errores:** `404` · `503`.

---

### `POST /api/v1/smpp-connectors/{cid}/start`

Inicia un conector SMPP y abre la sesión al SMSC.

**Path:** `cid`.

**Response 200:**
```json
{
  "data": { "cid": "carrier_mx", "status": "started", "sessions_count": 0, "last_error": null },
  "message": "Connector started"
}
```

> El estado final (`bound_TRX`, etc.) se refleja después de unos segundos en `GET /{cid}/status`.

**Errores:** `404` · `503`.

---

### `POST /api/v1/smpp-connectors/{cid}/stop`

Detiene un conector y cierra la sesión SMPP con `unbind`.

> Mensajes en tránsito pueden perderse. Detener cuando no haya tráfico activo.

**Response 200:**
```json
{
  "data": { "cid": "carrier_mx", "status": "stopped", "sessions_count": 0, "last_error": null },
  "message": "Connector stopped"
}
```

**Errores:** `404` · `503`.

---

### `GET /api/v1/smpp-connectors/{cid}/status`

Estado operacional actual del conector.

**Response 200:**
```json
{
  "data": {
    "cid": "carrier_mx",
    "status": "bound_TRX",
    "sessions_count": 1,
    "last_error": null
  }
}
```

**Valores posibles de `status`:**

| Valor | Significado |
|-------|-------------|
| `stopped` | Detenido manualmente |
| `started` | En ejecución, intentando conectar |
| `connecting` | Estableciendo conexión TCP |
| `bound_TRX` | Bound como transceiver (send+receive) |
| `bound_TX` | Bound como transmitter (sólo envío) |
| `bound_RX` | Bound como receiver (sólo recepción) |

**Errores:** `404` · `503`.

---

## HTTP Connectors

Webhooks donde Jasmin entrega mensajes MO (inbound). Cuando un SMS inbound es recibido y una ruta MO coincide, Jasmin hace `GET` o `POST` a la URL configurada.

> **Payload que envía Jasmin al webhook:** `from`, `to`, `content`, `binary`, `smsc-id`, `priority`, `coding`, `validity-period`, `tags`.

### `GET /api/v1/http-connectors/`

Lista todos los conectores HTTP.

**Response 200:**
```json
{
  "data": [
    {
      "cid": "webhook_crm",
      "url": "https://myapp.com/sms/inbound",
      "method": "POST"
    }
  ]
}
```

**Errores:** `503`.

---

### `GET /api/v1/http-connectors/{cid}`

Retorna un conector HTTP por su ID.

**Errores:** `404` · `503`.

---

### `POST /api/v1/http-connectors/`

Crea un conector HTTP nuevo.

**Body:**

| Campo | Tipo | Requerido | Valores aceptados | Ejemplo |
|-------|------|-----------|-------------------|---------|
| `cid` | string | Sí | 1–64 chars · `[a-zA-Z0-9_-]` | `"webhook_crm"` |
| `url` | string | Sí | URL completa con esquema | `"https://myapp.com/sms/inbound"` |
| `method` | enum | Sí | `"GET"` \| `"POST"` | `"POST"` |

**Ejemplo — webhook POST:**
```json
{
  "cid": "webhook_crm",
  "url": "https://myapp.com/sms/inbound",
  "method": "POST"
}
```

**Ejemplo — webhook GET con query string:**
```json
{
  "cid": "webhook_legacy",
  "url": "https://legacy.example.com/inbound.php",
  "method": "GET"
}
```

**Response 201:**
```json
{
  "data": { "cid": "webhook_crm", "url": "https://myapp.com/sms/inbound", "method": "POST" },
  "message": "HTTP connector created"
}
```

**Errores:** `409` (con `existing`) · `422` · `503`.

---

### `PATCH /api/v1/http-connectors/{cid}`

Actualiza URL o método.

**Body:**

| Campo | Tipo | Requerido | Valores |
|-------|------|-----------|---------|
| `url` | string | No | URL completa con esquema |
| `method` | enum | No | `"GET"` \| `"POST"` |

**Ejemplo:**
```json
{ "url": "https://newapp.com/api/sms/mo", "method": "POST" }
```

**Response 200:** `HttpConnectorOut` actualizado.

**Errores:** `404` · `422` · `503`.

---

### `DELETE /api/v1/http-connectors/{cid}`

Elimina un conector HTTP. Quitar referencias en rutas MO primero.

**Response 200:**
```json
{ "data": null, "message": "HTTP connector deleted" }
```

**Errores:** `404` · `503`.

---

## Filters — Filtros

Condiciones reutilizables adjuntas a rutas e interceptores. Cada tipo inspecciona un atributo diferente del mensaje.

### `GET /api/v1/filters/`

Lista todos los filtros.

**Response 200:**
```json
{
  "data": [
    { "fid": "ft_all", "type": "TransparentFilter", "routes": "MT MO", "description": "<T>", "params": {} },
    { "fid": "ft_src_mx", "type": "SourceAddrFilter", "routes": "MT", "description": "<SA (re=^52)>", "params": { "src_addr": "^52" } }
  ]
}
```

> `routes` y `description` sólo aparecen en el listado. Los `params` pueden usar abreviaciones internas de Jasmin (`src_addr` en lugar de `source_addr`).

**Errores:** `503`.

---

### `GET /api/v1/filters/{fid}`

Retorna un filtro por su FID. `routes` y `description` quedan vacíos en esta respuesta.

**Errores:** `404` · `503`.

---

### `POST /api/v1/filters/`

Crea un nuevo filtro.

**Body común:**

| Campo | Tipo | Requerido | Restricciones / Valores | Ejemplo |
|-------|------|-----------|-------------------------|---------|
| `fid` | string | Sí | 1–64 chars · `[a-zA-Z0-9_-]` | `"ft_src_mx"` |
| `type` | enum | Sí | ver tabla siguiente | `"SourceAddrFilter"` |
| `params` | object | Depende del tipo | claves dependen del tipo | `{ "source_addr": "^52" }` |

**Tipos de filtro disponibles y parámetros requeridos:**

| `type` | Clave en `params` | Tipo del valor | Valor de ejemplo |
|--------|------------------|----------------|------------------|
| `TransparentFilter` | _(ninguno)_ | `{}` | `{}` |
| `UserFilter` | `uid` | string (UID de usuario) | `{"uid": "user_mx_01"}` |
| `GroupFilter` | `gid` | string (GID de grupo) | `{"gid": "premium_customers"}` |
| `ConnectorFilter` | `cid` | string (CID conector SMPP) | `{"cid": "carrier_mx"}` |
| `SourceAddrFilter` | `source_addr` | regex | `{"source_addr": "^52"}` |
| `DestinationAddrFilter` | `destination_addr` | regex | `{"destination_addr": "^\\+1"}` |
| `ShortMessageFilter` | `short_message` | regex sobre el texto | `{"short_message": "^STOP"}` |
| `DateIntervalFilter` | `dateInterval` | `"YYYY-MM-DD;YYYY-MM-DD"` | `{"dateInterval": "2024-01-01;2024-12-31"}` |
| `TimeIntervalFilter` | `timeInterval` | `"HH:MM:SS;HH:MM:SS"` (24h) | `{"timeInterval": "08:00:00;18:00:00"}` |
| `TagFilter` | `tag` | integer | `{"tag": 99}` |
| `EvalPyFilter` | `pyCode` | expresión Python que retorne `bool` | `{"pyCode": "routable.pdu.params['source_addr'].startswith('52')"}` |

**Ejemplos por tipo:**

```json
{ "fid": "ft_all", "type": "TransparentFilter", "params": {} }
```

```json
{ "fid": "ft_user_mx", "type": "UserFilter", "params": { "uid": "user_mx_01" } }
```

```json
{ "fid": "ft_src_mx", "type": "SourceAddrFilter", "params": { "source_addr": "^52" } }
```

```json
{ "fid": "ft_dst_us", "type": "DestinationAddrFilter", "params": { "destination_addr": "^\\+?1\\d{10}$" } }
```

```json
{ "fid": "ft_stop_keyword", "type": "ShortMessageFilter", "params": { "short_message": "^(STOP|BAJA)$" } }
```

```json
{ "fid": "ft_business_hours", "type": "TimeIntervalFilter", "params": { "timeInterval": "09:00:00;18:00:00" } }
```

```json
{ "fid": "ft_q1_2024", "type": "DateIntervalFilter", "params": { "dateInterval": "2024-01-01;2024-03-31" } }
```

```json
{ "fid": "ft_tag_promo", "type": "TagFilter", "params": { "tag": 100 } }
```

```json
{
  "fid": "ft_mx_only",
  "type": "EvalPyFilter",
  "params": { "pyCode": "routable.pdu.params['source_addr'].startswith('52')" }
}
```

**Response 201:**
```json
{
  "data": { "fid": "ft_src_mx", "type": "SourceAddrFilter", "routes": "", "description": "", "params": {} },
  "message": "Filter created"
}
```

**Errores:** `409` (con `existing`) · `422` · `503`.

---

### `PATCH /api/v1/filters/{fid}`

Actualiza un filtro.

> Jasmin no tiene `filter --update`. Este endpoint **elimina y recrea** el filtro internamente; el `fid` se preserva.

**Body — los dos campos son requeridos (la actualización siempre reemplaza la definición completa):**

| Campo | Tipo | Requerido | Valores |
|-------|------|-----------|---------|
| `type` | enum | Sí | mismo set que en `POST` |
| `params` | object | Sí | claves dependen del nuevo `type` |

**Ejemplo — convertir un `SourceAddrFilter` en `DestinationAddrFilter`:**
```json
{
  "type": "DestinationAddrFilter",
  "params": { "destination_addr": "^\\+52" }
}
```

**Response 200:** `FilterOut` actualizado.

**Errores:** `404` · `422` · `503`.

---

### `DELETE /api/v1/filters/{fid}`

Elimina un filtro. Eliminar un filtro referenciado por rutas activas las deja sin filtro válido.

**Response 200:**
```json
{ "data": null, "message": "Filter deleted" }
```

**Errores:** `404` · `503`.

---

## MT Routes — Rutas salientes

Las rutas MT (Mobile Terminated) deciden qué conector SMPP usa Jasmin para entregar un mensaje outbound. Se evalúan en orden ascendente — gana la primera cuyos filtros coincidan. `DefaultRoute` (order 0) es el fallback.

### `GET /api/v1/mt-routes/`

Lista todas las rutas MT.

**Response 200:**
```json
{
  "data": [
    { "order": 0,  "type": "DefaultRoute",        "connectors": ["smppc(carrier_mx)"],      "filters": [], "rate": 0.05 },
    { "order": 10, "type": "StaticMTRoute",       "connectors": ["smppc(carrier_premium)"], "filters": [], "rate": 0.03 },
    { "order": 5,  "type": "RandomRoundrobinMTRoute", "connectors": ["smppc(c_a)", "smppc(c_b)"], "filters": [], "rate": 0.04 }
  ]
}
```

> `filters` siempre es `[]` en las respuestas; Jasmin no expone los FIDs en `route -s`.

**Errores:** `503`.

---

### `GET /api/v1/mt-routes/{order}`

Retorna una ruta MT por su número de orden.

**Path:** `order` (integer ≥ 0).

**Errores:** `404` · `503`.

---

### `POST /api/v1/mt-routes/`

Crea una ruta MT nueva.

**Body:**

| Campo | Tipo | Requerido | Valores aceptados | Descripción |
|-------|------|-----------|-------------------|-------------|
| `type` | enum | Sí | `DefaultRoute` \| `StaticMTRoute` \| `RandomRoundrobinMTRoute` \| `FailoverMTRoute` | Tipo de ruta |
| `order` | int ≥ 0 | Sí | `0` para DefaultRoute | Prioridad (menor = más prioritaria) |
| `connectors` | array string ≥ 1 | Sí | `["smppc(<cid>)", ...]` | IDs SMPP con prefijo `smppc(...)` |
| `filters` | array string | Condicional | `["<fid1>", ...]` | Requerido para `StaticMTRoute`; opcional para `RandomRoundrobinMTRoute`/`FailoverMTRoute` (auto-resuelto a TransparentFilter) |
| `rate` | float \| null | No | ≥ 0 (default `null` = gratis) | Costo por mensaje en crédito del usuario |

**Diferencias por tipo:**

| Tipo | Conectores | Filtros | Comportamiento |
|------|-----------|---------|----------------|
| `DefaultRoute` | 1 | no necesarios | Fallback global. Order forzado a 0 por Jasmin |
| `StaticMTRoute` | 1 | requeridos | Match exclusivo por filtros |
| `RandomRoundrobinMTRoute` | ≥ 2 | opcional (TransparentFilter automático si vacío) | Distribuye carga aleatoriamente |
| `FailoverMTRoute` | ≥ 2 | opcional | Usa el primer conector disponible; falla al siguiente |

**Ejemplo — DefaultRoute (fallback global):**
```json
{
  "type": "DefaultRoute",
  "order": 0,
  "connectors": ["smppc(carrier_mx)"],
  "rate": 0.05
}
```

**Ejemplo — StaticMTRoute (sólo para usuario premium):**
```json
{
  "type": "StaticMTRoute",
  "order": 10,
  "connectors": ["smppc(carrier_premium)"],
  "filters": ["ft_user_premium"],
  "rate": 0.03
}
```

**Ejemplo — RandomRoundrobinMTRoute (balanceo entre 2 carriers):**
```json
{
  "type": "RandomRoundrobinMTRoute",
  "order": 5,
  "connectors": ["smppc(carrier_a)", "smppc(carrier_b)"],
  "filters": ["ft_dst_mx"],
  "rate": 0.04
}
```

**Ejemplo — FailoverMTRoute (primario + backup):**
```json
{
  "type": "FailoverMTRoute",
  "order": 15,
  "connectors": ["smppc(carrier_primary)", "smppc(carrier_backup)"],
  "filters": ["ft_dst_us"],
  "rate": 0.07
}
```

**Response 201:**
```json
{
  "data": { "order": 10, "type": "StaticMTRoute", "connectors": ["smppc(carrier_premium)"], "filters": [], "rate": 0.03 },
  "message": "MT route created"
}
```

**Errores:**

- `400` — el tipo requiere filtros pero no hay TransparentFilter disponible:
  ```json
  { "detail": { "msg": "StaticMTRoute requires at least one filter; provide 'filters' or create a TransparentFilter first", "type": "AppHttpException" } }
  ```
- `409` — ya existe una ruta con ese `order` (incluye `existing`).
- `422` — validación.
- `503`.

---

### `PATCH /api/v1/mt-routes/{order}`

Actualiza una ruta MT.

> Jasmin no tiene comando de actualización. Este endpoint **flushea todas las rutas y las recrea** internamente, preservando el orden del resto.

**Path:** `order` (integer).

**Body — todos opcionales (sólo los enviados se actualizan):**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connectors` | array string | Nuevo listado de conectores. Omitir = conserva |
| `filters` | array string | Nuevo listado de filtros. Requerido si la ruta actual usa filtros non-TransparentFilter |
| `rate` | float \| null | Nueva tarifa |

**Ejemplo — sustituir conector y tarifa:**
```json
{ "connectors": ["smppc(carrier_backup)"], "rate": 0.08 }
```

**Ejemplo — agregar un filtro nuevo:**
```json
{ "filters": ["ft_dst_mx", "ft_business_hours"] }
```

**Errores:**

- `400` — la ruta usa filtros no recuperables; enviar `filters` explícitamente.
- `404` · `422` · `503`.

---

### `DELETE /api/v1/mt-routes/{order}`

Elimina una ruta MT por su order.

**Response 200:**
```json
{ "data": null, "message": "MT route deleted" }
```

**Errores:** `404` · `503`.

---

### `DELETE /api/v1/mt-routes/flush`

Elimina **todas** las rutas MT.

> **Destructivo.** Cualquier envío SMS fallará hasta recrear las rutas.

**Response 200:**
```json
{ "data": null, "message": "All MT routes flushed" }
```

**Errores:** `503`.

---

## MO Routes — Rutas entrantes

Las rutas MO (Mobile Originated) deciden qué conector HTTP recibe cada SMS inbound. Se evalúan en orden ascendente. `DefaultRoute` (order 0) es el fallback.

### `GET /api/v1/mo-routes/`

Lista todas las rutas MO.

**Response 200:**
```json
{
  "data": [
    { "order": 0,  "type": "DefaultRoute",          "connector": "http(webhook_crm)",     "connectors": [], "filters": [] },
    { "order": 10, "type": "StaticMORoute",         "connector": "http(webhook_support)", "connectors": [], "filters": [] },
    { "order": 20, "type": "FailoverMORoute",       "connector": null,                    "connectors": ["http(wh_a)", "http(wh_b)"], "filters": [] }
  ]
}
```

**Errores:** `503`.

---

### `GET /api/v1/mo-routes/{order}`

Retorna una ruta MO por su order.

**Errores:** `404` · `503`.

---

### `POST /api/v1/mo-routes/`

Crea una ruta MO nueva.

**Body:**

| Campo | Tipo | Requerido | Valores aceptados | Descripción |
|-------|------|-----------|-------------------|-------------|
| `type` | enum | Sí | `DefaultRoute` \| `StaticMORoute` \| `RandomRoundrobinMORoute` \| `FailoverMORoute` | Tipo de ruta |
| `order` | int ≥ 0 | Sí | — | Prioridad (DefaultRoute siempre se almacena en 0) |
| `connector` | string | Condicional | `"http(<cid>)"` o `"smpps(<cid>)"` | **Sólo** para `DefaultRoute` y `StaticMORoute` |
| `connectors` | array string ≥ 2 | Condicional | `["http(<cid>)", ...]` | **Sólo** para `RandomRoundrobinMORoute` y `FailoverMORoute` |
| `filters` | array string | Condicional | FIDs existentes | Requerido para `StaticMORoute` y multi-conector |

> Usar `connector` (singular) para tipos de un solo conector; `connectors` (plural) para multi-conector. Enviar el incorrecto retorna 422.

**Ejemplo — DefaultRoute:**
```json
{
  "type": "DefaultRoute",
  "order": 0,
  "connector": "http(webhook_crm)"
}
```

**Ejemplo — StaticMORoute (short codes a un webhook específico):**
```json
{
  "type": "StaticMORoute",
  "order": 10,
  "connector": "http(webhook_support)",
  "filters": ["ft_dst_short_code"]
}
```

**Ejemplo — FailoverMORoute (primario + backup):**
```json
{
  "type": "FailoverMORoute",
  "order": 20,
  "connectors": ["http(webhook_primary)", "http(webhook_backup)"],
  "filters": ["ft_all"]
}
```

**Ejemplo — RandomRoundrobinMORoute:**
```json
{
  "type": "RandomRoundrobinMORoute",
  "order": 30,
  "connectors": ["http(webhook_a)", "http(webhook_b)"],
  "filters": ["ft_all"]
}
```

**Response 201:** `MoRouteOut` con `connector` o `connectors` populado según el tipo.

**Errores:** `400` (tipo requiere filtros sin TransparentFilter) · `409` (con `existing`) · `422` (campo `connector`/`connectors` incorrecto) · `503`.

---

### `PATCH /api/v1/mo-routes/{order}`

Actualiza una ruta MO. Internamente flushea y recrea.

**Body — todos opcionales:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connector` | string | Nuevo conector único (para DefaultRoute / StaticMORoute) |
| `connectors` | array string | Nuevo listado (para multi-conector) |
| `filters` | array string | Nuevo listado de FIDs |

**Ejemplo:**
```json
{ "connector": "http(webhook_v2)" }
```

**Errores:** `400` · `404` · `422` · `503`.

---

### `DELETE /api/v1/mo-routes/{order}`

Elimina una ruta MO.

**Response 200:**
```json
{ "data": null, "message": "MO route deleted" }
```

**Errores:** `404` · `503`.

---

### `DELETE /api/v1/mo-routes/flush`

Elimina **todas** las rutas MO.

> **Destructivo.** Los SMS inbound no se entregarán hasta recrear las rutas.

**Response 200:**
```json
{ "data": null, "message": "All MO routes flushed" }
```

**Errores:** `503`.

---

## MT Interceptors

Los interceptores MT ejecutan scripts Python sobre cada mensaje outbound **antes del enrutamiento**. Pueden inspeccionar, modificar (tags), o rechazar mensajes.

### `GET /api/v1/mt-interceptors/`

Lista todos los interceptores MT.

**Response 200:**
```json
{
  "data": [
    { "order": 0,  "type": "DefaultInterceptor",   "filters": [], "script_path": "/etc/jasmin/scripts/mt_0.py"  },
    { "order": 10, "type": "StaticMTInterceptor",  "filters": [], "script_path": "/etc/jasmin/scripts/mt_10.py" }
  ]
}
```

> `filters` siempre es `[]` (FIDs no recuperables). Los archivos `.py` persisten en disco aunque se elimine el interceptor.

**Errores:** `503`.

---

### `GET /api/v1/mt-interceptors/{order}`

Retorna un interceptor MT por su order.

**Errores:** `404` · `503`.

---

### `POST /api/v1/mt-interceptors/`

Crea un interceptor MT con script Python. El script se guarda en `JASMIN_SCRIPTS_DIR` (default `/etc/jasmin/scripts`) como `mt_{order}.py`.

**Body:**

| Campo | Tipo | Requerido | Valores aceptados | Descripción |
|-------|------|-----------|-------------------|-------------|
| `type` | enum | Sí | `"DefaultInterceptor"` \| `"StaticMTInterceptor"` | Default aplica a todos los MT · Static sólo a los que matchean filtros |
| `order` | int ≥ 0 | Sí | — | Prioridad |
| `filters` | array string | Condicional | FIDs existentes | Requerido para `StaticMTInterceptor`; ignorado para `DefaultInterceptor` |
| `script` | string | Sí | Python módulo válido (se compila antes de guardar) | Use `\n` para newlines |

**API del objeto `routable` dentro del script:**

| Llamada | Efecto |
|---------|--------|
| `routable.reject()` | Rechaza el mensaje |
| `routable.addTag(n)` | Agrega tag numérico (int) |
| `routable.pdu.params['source_addr']` | Acceso a la dirección origen |
| `routable.pdu.params['destination_addr']` | Acceso a la dirección destino |
| `routable.pdu.params['short_message']` | Acceso al contenido (bytes) |

**Restricción importante:** El script debe ser un **módulo** Python válido. **NO** usar `return` a nivel de módulo (causa `SyntaxError` y se rechaza con 422).

**Ejemplo — pass-through (no acción):**
```json
{
  "type": "DefaultInterceptor",
  "order": 0,
  "filters": [],
  "script": "# pass-through\n"
}
```

**Ejemplo — rechazar mensajes de un usuario:**
```json
{
  "type": "StaticMTInterceptor",
  "order": 10,
  "filters": ["ft_user_blocked"],
  "script": "routable.reject()\n"
}
```

**Ejemplo — agregar tag a mensajes de México:**
```json
{
  "type": "StaticMTInterceptor",
  "order": 5,
  "filters": ["ft_src_mx"],
  "script": "routable.addTag(52)\n"
}
```

**Ejemplo — modificar el sender ID:**
```json
{
  "type": "DefaultInterceptor",
  "order": 1,
  "filters": [],
  "script": "routable.pdu.params['source_addr'] = b'InfoMX'\n"
}
```

**Response 201:**
```json
{
  "data": { "order": 10, "type": "StaticMTInterceptor", "filters": [], "script_path": "/etc/jasmin/scripts/mt_10.py" },
  "message": "MT interceptor created"
}
```

**Errores:**

- `422` — script Python con error de sintaxis:
  ```json
  { "detail": [ { "loc": ["body", "script"], "msg": "Value error, Script is not valid Python: invalid syntax", "type": "value_error" } ] }
  ```
- `409` (con `existing`) · `503`.

---

### `PATCH /api/v1/mt-interceptors/{order}`

Actualiza un interceptor MT. Internamente flushea todos los MT interceptors y los recrea.

**Body — ambos opcionales:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `filters` | array string | Nuevo listado. `[]` = sin filtros |
| `script` | string | Nuevo código Python. Omitir = reutiliza el archivo en disco |

> Si el archivo en disco fue borrado y no se envía `script`, retorna 400.

**Ejemplo — reemplazar script:**
```json
{ "script": "routable.addTag(999)\n" }
```

**Ejemplo — sólo cambiar filtros:**
```json
{ "filters": ["ft_user_premium"] }
```

**Errores:** `400` (script en disco no encontrado) · `404` · `422` · `503`.

---

### `DELETE /api/v1/mt-interceptors/{order}`

Elimina un interceptor MT. **El archivo `.py` en disco NO se elimina.**

**Response 200:**
```json
{ "data": null, "message": "MT interceptor deleted" }
```

**Errores:** `404` · `503`.

---

### `DELETE /api/v1/mt-interceptors/flush`

Elimina **todos** los interceptores MT. Los archivos en disco no se eliminan.

**Response 200:**
```json
{ "data": null, "message": "All MT interceptors flushed" }
```

**Errores:** `503`.

---

## MO Interceptors

Los interceptores MO ejecutan scripts Python sobre cada mensaje **inbound** antes del enrutamiento al HTTP connector. Misma API que MT interceptors, con `type` `DefaultInterceptor` o `StaticMOInterceptor`.

### `GET /api/v1/mo-interceptors/`

Lista todos los interceptores MO. Estructura idéntica a MT, con `script_path` prefijado por `mo_`.

**Errores:** `503`.

---

### `GET /api/v1/mo-interceptors/{order}`

Retorna un interceptor MO por su order.

**Errores:** `404` · `503`.

---

### `POST /api/v1/mo-interceptors/`

Crea un interceptor MO.

**Body:**

| Campo | Tipo | Requerido | Valores aceptados |
|-------|------|-----------|-------------------|
| `type` | enum | Sí | `"DefaultInterceptor"` \| `"StaticMOInterceptor"` |
| `order` | int ≥ 0 | Sí | — |
| `filters` | array string | Condicional | FIDs (requerido para Static) |
| `script` | string | Sí | Python módulo válido |

**Ejemplo — bloquear inbound de un conector:**
```json
{
  "type": "StaticMOInterceptor",
  "order": 10,
  "filters": ["ft_conn_blocked"],
  "script": "routable.reject()\n"
}
```

**Ejemplo — taggear inbound de México:**
```json
{
  "type": "StaticMOInterceptor",
  "order": 5,
  "filters": ["ft_src_mx_inbound"],
  "script": "routable.addTag(52)\n"
}
```

**Response 201:**
```json
{
  "data": { "order": 10, "type": "StaticMOInterceptor", "filters": [], "script_path": "/etc/jasmin/scripts/mo_10.py" },
  "message": "MO interceptor created"
}
```

**Errores:** `422` (script inválido) · `409` (con `existing`) · `503`.

---

### `PATCH /api/v1/mo-interceptors/{order}`

Actualiza un interceptor MO.

**Body:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `filters` | array string \| null | Nuevo listado |
| `script` | string \| null | Nuevo código Python (omitir = reutilizar disco) |

**Ejemplo:**
```json
{ "script": "routable.addTag(100)\n" }
```

**Errores:** `400` · `404` · `422` · `503`.

---

### `DELETE /api/v1/mo-interceptors/{order}`

Elimina un interceptor MO. Archivo en disco se conserva.

**Response 200:**
```json
{ "data": null, "message": "MO interceptor deleted" }
```

**Errores:** `404` · `503`.

---

### `DELETE /api/v1/mo-interceptors/flush`

Elimina **todos** los interceptores MO.

**Response 200:**
```json
{ "data": null, "message": "All MO interceptors flushed" }
```

**Errores:** `503`.

---

## SMPP Server

Configuración del servidor SMPP inbound de Jasmin (al que se conectan los clientes SMPP externos / ESME).

### `GET /api/v1/smpp-server/`

Retorna la configuración del SMPP server leída desde `/etc/jasmin/jasmin.cfg`.

> **Solo lectura.** Cambios requieren editar el archivo y reiniciar Jasmin.

**Response 200:**
```json
{
  "data": {
    "host": "0.0.0.0",
    "port": 2775,
    "max_bindings": null
  }
}
```

| Campo | Tipo | Default Jasmin | Descripción |
|-------|------|----------------|-------------|
| `host` | string | `0.0.0.0` | Dirección de bind del servidor SMPP |
| `port` | int | `2775` | Puerto TCP |
| `max_bindings` | int \| null | `null` | Máx sesiones SMPP simultáneas (`null` = default Jasmin) |

---

## SMS — Envío y consultas

Endpoints de envío y consulta de balance/tarifa. **No usan `X-API-Key`**: autentican con credenciales del usuario Jasmin (`username`/`password`) en el cuerpo o query string.

### `POST /api/v1/sms/send`

Envía un SMS outbound a través de la HTTP API de Jasmin.

**Body:**

| Campo | Tipo | Requerido | Valores aceptados | Default | Descripción |
|-------|------|-----------|-------------------|---------|-------------|
| `username` | string | Sí | UID del usuario Jasmin | — | Autenticación |
| `password` | string | Sí | Contraseña del usuario | — | Autenticación |
| `to` | string | Sí | MSISDN (E.164 recomendado) | — | Destino. Ej: `+525512345678` |
| `content` | string | Sí | Texto del mensaje | — | UTF-8 |
| `from` | string | No | Sender ID o MSISDN | — | Requiere `mt_auth_src_addr=true` |
| `coding` | int | No | `0`=GSM7, `1`=Binary, `8`=UCS-2 | `0` | Data coding scheme |
| `dlr` | enum | No | `"yes"` \| `"no"` | `"no"` | Solicitar delivery receipt. Ignorado con `DLR_ENABLED=true` (siempre se solicita) |
| `dlr_params` | dict | No | Ej. `{"org_id": 12}` | — | Params concatenados como query a la `DLR_URL` centralizada. Solo con `DLR_ENABLED=true` |
| `dlr_url` | string | No | URL completa | — | Solo modo legacy (`DLR_ENABLED=false`); ignorado si el DLR está centralizado |
| `dlr_level` | int | No | `1`=final, `2`=intermedio, `3`=ambos | env `DLR_LEVEL` | Nivel del DLR |
| `dlr_method` | enum | No | `"GET"` \| `"POST"` | env `DLR_METHOD` | Método HTTP del callback DLR |
| `priority` | int | No | `0`–`3` | — | Requiere `mt_auth_priority=true` |
| `schedule_delivery_time` | string | No | `YYMMDDHHmmss000R` (relativo) o `YYMMDDHHmmssNNNp` (absoluto) | — | Envío programado |
| `validity_period` | string | No | mismo formato | — | Tiempo máximo de validez |
| `tags` | array int | No | lista de enteros | `[]` | Tags numéricos |

**Ejemplo básico (sólo texto):**
```json
{
  "username": "user_mx_01",
  "password": "Secr3t!2024",
  "to": "+525512345678",
  "content": "Tu código de verificación es: 482931"
}
```

**Ejemplo con sender personalizado y DLR:**
```json
{
  "username": "user_mx_01",
  "password": "Secr3t!2024",
  "to": "+525512345678",
  "content": "Tu pedido #98234 fue enviado.",
  "from": "MiTienda",
  "coding": 0,
  "dlr_params": { "org_id": 12 }
}
```
> Con el DLR centralizado (`DLR_ENABLED=true`), la URL destino la fija el gateway
> (`DLR_URL`) y **no** se envía en el body: solo se aportan `dlr_params`, que se
> concatenan como query params a esa URL (ej. `DLR_URL?org_id=12`). Todos los
> envíos solicitan DLR. Los campos `dlr_url`/`dlr_method`/`dlr_level` solo aplican
> en modo legacy (`DLR_ENABLED=false`).

**Ejemplo SMS Unicode (emoji/acentos):**
```json
{
  "username": "user_mx_01",
  "password": "Secr3t!2024",
  "to": "+525512345678",
  "content": "¡Promoción! 🎁 50% en tu próxima compra",
  "coding": 8
}
```

**Ejemplo SMS programado (+1 hora):**
```json
{
  "username": "user_mx_01",
  "password": "Secr3t!2024",
  "to": "+525512345678",
  "content": "Recordatorio: tu cita es a las 15:00",
  "schedule_delivery_time": "000000010000000R"
}
```

**Response 200:**
```json
{ "data": { "message_id": "40d2a7f3-1234-5678-abcd-ef0123456789" } }
```

**Errores:**

- `400` — balance insuficiente / ruta no encontrada / interceptor rechazó:
  ```json
  { "detail": { "msg": "Error \"No route found\"", "type": "AppHttpException" } }
  ```
- `401` — credenciales inválidas.
- `503` — Jasmin no disponible.

---

### `POST /api/v1/sms/send/binary`

Envía un SMS binario con contenido hex-encoded (WAP push, vCard, ringtones).

**Body:**

| Campo | Tipo | Requerido | Valores | Default | Descripción |
|-------|------|-----------|---------|---------|-------------|
| `username` | string | Sí | UID usuario | — | — |
| `password` | string | Sí | Contraseña | — | — |
| `to` | string | Sí | MSISDN | — | — |
| `hex_content` | string | Sí | hex (par de chars por byte) | — | Ej: `48656c6c6f` = "Hello" |
| `coding` | int | No | `1`=Binary, `4`=8-bit, `8`=UCS-2 | `1` | Coding |
| `from` | string | No | Sender ID | — | — |
| `dlr` | enum | No | `"yes"` \| `"no"` | `"no"` | Ignorado con `DLR_ENABLED=true` |
| `dlr_params` | dict | No | Ej. `{"org_id": 12}` | — | Query params a la `DLR_URL` centralizada. Solo con `DLR_ENABLED=true` |
| `dlr_url` | string | No | URL | — | Solo legacy; ignorado si el DLR está centralizado |
| `dlr_level` | int | No | `1` \| `2` \| `3` | env `DLR_LEVEL` | — |
| `dlr_method` | enum | No | `"GET"` \| `"POST"` | env `DLR_METHOD` | — |

**Ejemplo — enviar "Hello World" como binario:**
```json
{
  "username": "user_mx_01",
  "password": "Secr3t!2024",
  "to": "+525512345678",
  "hex_content": "48656c6c6f20576f726c64",
  "coding": 1,
  "from": "MyApp"
}
```

**Response 200:**
```json
{ "data": { "message_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab" } }
```

**Errores:** `400` · `401` · `503`.

---

### `GET /api/v1/sms/rate`

Consulta la tarifa que se cobraría al usuario para un destino dado.

**Query parameters:**

| Parámetro | Tipo | Requerido | Ejemplo |
|-----------|------|-----------|---------|
| `username` | string | Sí | `user_mx_01` |
| `password` | string | Sí | `Secr3t!2024` |
| `to` | string | Sí | `+525512345678` |
| `from` | string | No | `MiTienda` |
| `content` | string | No | `Hello` |

**Ejemplo de solicitud:**
```
GET /api/v1/sms/rate?username=user_mx_01&password=Secr3t%212024&to=%2B525512345678
```

**Response 200:**
```json
{
  "data": {
    "rate": 0.05,
    "unit": "per_message",
    "connector_id": "carrier_mx"
  }
}
```

**Errores:**

- `412` — sin ruta válida para el destino:
  ```json
  { "detail": { "msg": "Error \"No route found\"", "type": "AppHttpException" } }
  ```
- `401` · `503`.

---

### `GET /api/v1/sms/balance`

Consulta el balance y cuota SMS del usuario.

**Query parameters:**

| Parámetro | Tipo | Requerido | Ejemplo |
|-----------|------|-----------|---------|
| `username` | string | Sí | `user_mx_01` |
| `password` | string | Sí | `Secr3t!2024` |

**Ejemplo:**
```
GET /api/v1/sms/balance?username=user_mx_01&password=Secr3t%212024
```

**Response 200:**
```json
{
  "data": { "balance": 87.50, "sms_count": null }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `balance` | float \| null | Crédito restante (`null` = ilimitado) |
| `sms_count` | int \| null | SMS restantes en la cuota (`null` = ilimitado o no aplica) |

**Errores:** `401` · `503`.

---

## Stats — Estadísticas

Estadísticas en tiempo real de Jasmin. Todas se resetean al reiniciar Jasmin.

### `GET /api/v1/stats/`

Overview consolidado de todas las estadísticas (4 llamadas paralelas a jcli).

**Response 200:**
```json
{
  "data": {
    "smpp_connectors": [
      {
        "cid": "carrier_mx",
        "connected_at": "2024-01-15 08:30:00",
        "bound_at": "2024-01-15 08:30:01",
        "disconnected_at": null,
        "submits": "1500/1498",
        "delivers": "0/0",
        "qos_errors": 0,
        "other_errors": 2
      }
    ],
    "users": [
      {
        "uid": "user_mx_01",
        "smpp_bound_connections": 1,
        "smpp_last_activity": "2024-01-15 12:00:00",
        "http_request_count": 450,
        "http_last_activity": "2024-01-15 12:05:00"
      }
    ],
    "http_api": {
      "request_count": 1200,
      "success_count": 1195,
      "auth_error_count": 2,
      "route_error_count": 3,
      "interceptor_error_count": 0,
      "interceptor_count": 1200,
      "throughput_error_count": 0,
      "charging_error_count": 0,
      "server_error_count": 0
    },
    "smpp_server_api": {
      "connected_count": 3,
      "connect_count": 5,
      "disconnect_count": 2,
      "bound_trx_count": 2,
      "bound_rx_count": 1,
      "bound_tx_count": 0,
      "submit_sm_count": 800,
      "deliver_sm_count": 45
    }
  }
}
```

> `submits` formato `"requested/accepted"` — ej: `"1500/1498"` = 1500 enviados, 1498 aceptados.

**Errores:** `503`.

---

### `GET /api/v1/stats/smpp-connectors/{cid}`

Estadísticas detalladas de un conector SMPP.

**Path:** `cid` (Identifier).

**Response 200:**
```json
{
  "data": {
    "cid": "carrier_mx",
    "created_at": "2024-01-15 08:00:00",
    "connected_at": "2024-01-15 08:30:00",
    "bound_at": "2024-01-15 08:30:01",
    "disconnected_at": null,
    "last_received_pdu_at": "2024-01-15 12:10:00",
    "last_sent_pdu_at": "2024-01-15 12:10:05",
    "connected_count": 1,
    "bound_count": 1,
    "disconnected_count": 0,
    "submit_sm_request_count": 1500,
    "submit_sm_count": 1498,
    "deliver_sm_count": 45,
    "elink_count": 720,
    "throttling_error_count": 0,
    "other_submit_error_count": 2,
    "interceptor_error_count": 0,
    "interceptor_count": 1500
  }
}
```

> Timestamps `null` = el evento nunca ocurrió desde el último reinicio.

**Errores:** `404` · `503`.

---

### `GET /api/v1/stats/users/{uid}`

Estadísticas detalladas de un usuario (SMPP + HTTP).

**Path:** `uid` (Identifier).

**Response 200:**
```json
{
  "data": {
    "uid": "user_mx_01",
    "smpp_bind_count": 2,
    "smpp_unbind_count": 0,
    "smpp_bound_connections": 1,
    "smpp_submit_sm_request_count": 800,
    "smpp_submit_sm_count": 798,
    "smpp_deliver_sm_count": 0,
    "smpp_elink_count": 240,
    "smpp_throttling_error_count": 0,
    "smpp_other_submit_error_count": 2,
    "smpp_last_activity_at": "2024-01-15 12:00:00",
    "http_connects_count": 450,
    "http_submit_sm_request_count": 450,
    "http_balance_request_count": 5,
    "http_rate_request_count": 3,
    "http_last_activity_at": "2024-01-15 12:05:00"
  }
}
```

**Errores:** `404` · `503`.

---

### `GET /api/v1/stats/http-api`

Estadísticas agregadas de la HTTP API (todos los usuarios).

**Response 200:**
```json
{
  "data": {
    "created_at": "2024-01-15 08:00:00",
    "last_request_at": "2024-01-15 12:10:00",
    "last_success_at": "2024-01-15 12:09:58",
    "request_count": 1200,
    "success_count": 1195,
    "auth_error_count": 2,
    "route_error_count": 1,
    "interceptor_error_count": 0,
    "interceptor_count": 1200,
    "throughput_error_count": 0,
    "charging_error_count": 2,
    "server_error_count": 0
  }
}
```

**Errores:** `503`.

---

### `GET /api/v1/stats/smpp-server-api`

Estadísticas del servidor SMPP inbound (todos los clientes).

**Response 200:**
```json
{
  "data": {
    "created_at": "2024-01-15 08:00:00",
    "last_received_pdu_at": "2024-01-15 12:10:00",
    "last_sent_pdu_at": "2024-01-15 12:10:01",
    "connected_count": 3,
    "connect_count": 5,
    "disconnect_count": 2,
    "bound_trx_count": 2,
    "bound_rx_count": 1,
    "bound_tx_count": 0,
    "bind_trx_count": 4,
    "bind_rx_count": 1,
    "bind_tx_count": 0,
    "unbind_count": 0,
    "submit_sm_request_count": 800,
    "submit_sm_count": 798,
    "deliver_sm_count": 45,
    "elink_count": 300,
    "throttling_error_count": 0,
    "other_submit_error_count": 2,
    "interceptor_error_count": 0,
    "interceptor_count": 800
  }
}
```

**Errores:** `503`.

---

## Insights — Vistas agregadas

Endpoints que combinan múltiples fuentes en una sola llamada. Ideales para dashboards y admin UIs.

### `GET /api/v1/insights/overview`

Conteos de todos los recursos + estado de conectividad.

**Response 200:**
```json
{
  "data": {
    "status": "ok",
    "telnet_connected": true,
    "jasmin_http_reachable": true,
    "counts": {
      "users": 12,
      "groups": 3,
      "smpp_connectors": 4,
      "http_connectors": 2,
      "mt_routes": 5,
      "mo_routes": 2,
      "filters": 8,
      "mt_interceptors": 1,
      "mo_interceptors": 0
    }
  }
}
```

**Errores:** `503`.

---

### `GET /api/v1/insights/users/{uid}/profile`

Perfil completo de usuario: configuración + grupo + estadísticas.

**Path:** `uid`.

**Response 200:**
```json
{
  "data": {
    "user": { "uid": "user_mx_01", "gid": "premium_customers", "enabled": true, "balance": 150.0, "mt_throughput": 10.0 },
    "group": { "gid": "premium_customers", "enabled": true },
    "stats": {
      "smpp_bound_connections": 1,
      "smpp_last_activity_at": "2024-01-15 12:00:00",
      "http_connects_count": 450,
      "http_last_activity_at": "2024-01-15 12:05:00"
    }
  }
}
```

**Errores:** `404` · `503`.

---

### `GET /api/v1/insights/groups/{gid}/members`

Grupo con todos sus usuarios y actividad.

**Path:** `gid`.

**Response 200:**
```json
{
  "data": {
    "group": { "gid": "premium_customers", "enabled": true },
    "members": [
      {
        "uid": "user_mx_01",
        "enabled": true,
        "smpp_bound_connections": 1,
        "http_request_count": 450,
        "smpp_last_activity": "2024-01-15 12:00:00",
        "http_last_activity": "2024-01-15 12:05:00"
      }
    ],
    "total": 1
  }
}
```

**Errores:** `404` · `503`.

---

### `GET /api/v1/insights/connectors/smpp/health`

Dashboard de salud de todos los conectores SMPP.

**Response 200:**
```json
{
  "data": {
    "connectors": [
      {
        "cid": "carrier_mx",
        "status": "bound_TRX",
        "sessions_count": 1,
        "connected_at": "2024-01-15 08:30:00",
        "bound_at": "2024-01-15 08:30:01",
        "disconnected_at": null,
        "submits": "1500/1498",
        "delivers": "0/0",
        "qos_errors": 0,
        "other_errors": 2
      }
    ],
    "total": 4,
    "connected": 3,
    "with_errors": 1
  }
}
```

**Errores:** `503`.

---

### `GET /api/v1/insights/connectors/smpp/{cid}/detail`

Vista completa de un conector: configuración + estado + estadísticas.

**Path:** `cid`.

**Response 200:**
```json
{
  "data": {
    "connector": { "cid": "carrier_mx", "host": "smpp.carrier.com", "port": 2775, "username": "jasmin_prod", "bind_to": "transceiver" },
    "status": { "cid": "carrier_mx", "status": "bound_TRX", "sessions_count": 1, "last_error": null },
    "stats": { "submit_sm_request_count": 1500, "submit_sm_count": 1498, "other_submit_error_count": 2 }
  }
}
```

**Errores:** `404` · `503`.

---

### `GET /api/v1/insights/connectors/smpp/{cid}/usage`

Conector + todas las rutas MT que lo referencian (blast radius).

**Response 200:**
```json
{
  "data": {
    "cid": "carrier_mx",
    "connector": { "cid": "carrier_mx", "host": "smpp.carrier.com", "port": 2775 },
    "mt_routes": [
      { "order": 0,  "type": "DefaultRoute",  "rate": 0.05 },
      { "order": 10, "type": "StaticMTRoute", "rate": 0.03 }
    ],
    "mt_routes_count": 2
  }
}
```

**Errores:** `404` · `503`.

---

### `GET /api/v1/insights/sessions/active`

Snapshot en tiempo real de sesiones activas (usuarios + conectores + SMPP server).

**Response 200:**
```json
{
  "data": {
    "active_users": [
      { "uid": "user_mx_01", "smpp_bound_connections": 1, "smpp_last_activity": "2024-01-15 12:00:00", "http_request_count": 450, "http_last_activity": "2024-01-15 12:05:00" }
    ],
    "active_connectors": [
      { "cid": "carrier_mx", "status": "bound_TRX", "sessions_count": 1, "bound_at": "2024-01-15 08:30:01", "submits": "1500/1498" }
    ],
    "smpp_server": { "connected_count": 3, "submit_sm_count": 800, "bound_trx_count": 2 },
    "total_bound_users": 1,
    "total_connected_connectors": 3
  }
}
```

**Errores:** `503`.

---

### `GET /api/v1/insights/routes/map`

Mapa de topología completa de rutas MT y MO.

**Response 200:**
```json
{
  "data": {
    "mt_routes": [
      { "order": 0,  "type": "DefaultRoute",  "connectors": ["smppc(carrier_mx)"],      "filter_indicator": "",                       "rate": 0.05 },
      { "order": 10, "type": "StaticMTRoute", "connectors": ["smppc(carrier_premium)"], "filter_indicator": "<U (uid=user_premium)>", "rate": 0.03 }
    ],
    "mo_routes": [
      { "order": 0, "type": "DefaultRoute", "connector": "http(webhook_crm)", "filter_indicator": "" }
    ],
    "total_mt": 2,
    "total_mo": 1
  }
}
```

> `filter_indicator`: string raw de Jasmin. `<T>` = TransparentFilter. Vacío = sin filtros.

**Errores:** `503`.

---

## System — Mantenimiento

Operaciones de mantenimiento. Todas las operaciones de escritura del API llaman `persist` automáticamente, así que estos endpoints sólo se necesitan en escenarios excepcionales.

### `POST /api/v1/system/persist`

Guarda la configuración en memoria de Jasmin a disco.

**Response 200:**
```json
{ "data": "Persistence storage updated" }
```

**Errores:** `503`.

---

### `POST /api/v1/system/reload`

Recarga la configuración desde disco a memoria, **descartando** cambios en memoria no persistidos.

> Usar tras editar manualmente archivos en `/etc/jasmin/store/`.

**Response 200:**
```json
{ "data": "Configuration reloaded successfully" }
```

**Errores:** `503`.

---

### `POST /api/v1/system/reconnect`

Fuerza reconexión inmediata de la sesión Telnet con jcli.

**Response 200:**
```json
{ "data": "Reconnected successfully" }
```

**Errores:**

- `503` — reconexión fallida (Jasmin sigue caído):
  ```json
  { "detail": { "msg": "Jasmin is not available", "type": "AppHttpException" } }
  ```

---

### `GET /api/v1/system/session`

Estado actual de la sesión Telnet con jcli.

**Response 200:**
```json
{
  "data": {
    "connected": true,
    "reconnecting": false,
    "uptime_seconds": 3600.5,
    "host": "127.0.0.1",
    "port": 8990
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connected` | boolean | `true` si la sesión Telnet está activa |
| `reconnecting` | boolean | `true` si hay reconexión en curso |
| `uptime_seconds` | float \| null | Segundos desde establecida la sesión (`null` si no conectado) |
| `host` | string | Host Telnet (env: `JASMIN_TELNET_HOST`) |
| `port` | int | Puerto Telnet (env: `JASMIN_TELNET_PORT`) |

> Siempre retorna 200, incluso cuando Jasmin no está conectado.

---

## Notas de integración

### Orden de creación recomendado

Setup desde cero:

1. **Grupos** → `POST /api/v1/groups/`
2. **Filtros** → `POST /api/v1/filters/` (incluir al menos un `TransparentFilter`)
3. **Conectores SMPP** → `POST /api/v1/smpp-connectors/` + `POST /{cid}/start`
4. **Conectores HTTP** → `POST /api/v1/http-connectors/`
5. **Usuarios** → `POST /api/v1/users/` (el grupo debe existir)
6. **Rutas MT** → `POST /api/v1/mt-routes/` (conectores deben existir)
7. **Rutas MO** → `POST /api/v1/mo-routes/`
8. **Interceptores** → `POST /api/v1/mt-interceptors/` / `POST /api/v1/mo-interceptors/`

### Sintaxis de IDs de conectores en rutas e interceptores

| Tipo | Sintaxis | Ejemplo |
|------|----------|---------|
| SMPP outbound | `smppc(<cid>)` | `smppc(carrier_mx)` |
| HTTP outbound (MO routes) | `http(<cid>)` | `http(webhook_crm)` |
| SMPP server (inbound) | `smpps(<cid>)` | `smpps(user_mx_01)` |

### DefaultRoute siempre en order 0

Jasmin ignora el `order` enviado para `DefaultRoute` y lo fuerza a 0. Intentar crear dos `DefaultRoute` retorna 409.

### Filtros no recuperables en rutas/interceptores

`filters` siempre retorna `[]` en respuestas — Jasmin no expone los FIDs en `route -s`/`interceptor -s`. Para `PATCH` en rutas/interceptores con filtros non-TransparentFilter, enviar `filters` explícitamente.

### Conector SMPP: flujo de actualización

```
1. POST /api/v1/smpp-connectors/{cid}/stop    → detener
2. PATCH /api/v1/smpp-connectors/{cid}        → actualizar
3. POST /api/v1/smpp-connectors/{cid}/start   → reiniciar
```

Jasmin no aplica cambios a una sesión SMPP activa.

### Respuesta 409 con recurso existente

Todos los `POST` de creación retornan 409 con el objeto `existing` en `detail` cuando el recurso ya existe — el cliente no necesita un GET adicional para identificar el conflicto.

### Scripts de interceptores

- Se guardan en `JASMIN_SCRIPTS_DIR` (default `/etc/jasmin/scripts`) como `mt_{order}.py` o `mo_{order}.py`.
- El script se valida con `compile()` antes de guardar — un script con error de sintaxis retorna 422.
- Al eliminar un interceptor, el archivo `.py` **no** se elimina.
- `return` a nivel de módulo es inválido en Python — usar `routable.reject()` para abortar el mensaje.

### Diferencia `connector` vs `connectors` en MO routes

- `connector` (singular) → `DefaultRoute`, `StaticMORoute`
- `connectors` (plural, array ≥ 2) → `RandomRoundrobinMORoute`, `FailoverMORoute`

Enviar el campo equivocado retorna 422.

### Auto-persist

Toda operación de escritura exitosa (POST/PATCH/DELETE) llama a `persist` automáticamente. La configuración sobrevive reinicios sin acción adicional.

### Variables de entorno relevantes

| Variable | Default | Descripción |
|----------|---------|-------------|
| `API_KEY` | — | Valor del header `X-API-Key` |
| `APP_ENV` | — | `development` \| `production` |
| `JASMIN_TELNET_HOST` | `127.0.0.1` | Host jcli |
| `JASMIN_TELNET_PORT` | `8990` | Puerto jcli |
| `JASMIN_TELNET_TIMEOUT` | `10` | Segundos por comando jcli |
| `JASMIN_HTTP_HOST` | `localhost` | Host HTTP API Jasmin |
| `JASMIN_HTTP_PORT` | `1401` | Puerto HTTP API Jasmin |
| `JASMIN_SCRIPTS_DIR` | `/etc/jasmin/scripts` | Directorio de scripts de interceptores |
| `DOCS_ENABLED` | — | `True` habilita `/api/v1/docs` y `/api/v1/redoc` |
| `RATE_LIMIT_DEFAULT` | `200/minute` | Rate limit por IP |
| `REQUEST_MAX_SIZE_MB` | `10` | Máx tamaño del body |
| `CORS_ORIGINS` | — | Lista de orígenes CORS (`*` para todos) |

---

*Documentación generada para Jasmin SMS Gateway Admin API v1. Para arquitectura interna y patrones de implementación, ver `CLAUDE.md`.*
