# Plan: jasmin-admin-api — API REST Sidecar para Jasmin SMS Gateway

> Slug: `jasmin-admin-api`
> Creado: 2026-05-02
> Servicio(s): `jasmin-admin-api` (nuevo), `database/sms`
> Estado: `pendiente`

---

## Objective

Crear el servicio `jasmin-admin-api`: un sidecar REST API que vive en el mismo servidor/pod que Jasmin SMS Gateway y actúa como único punto de acceso externo para administración y envío. Jasmin nunca expone sus puertos (Telnet 8990, HTTP 1401) fuera del servidor. "Terminado" significa que el orchestrator puede realizar cualquier operación de Jasmin exclusivamente a través de este API, sin conexión directa a Telnet ni a la HTTP API de Jasmin.

---

## Context

El `sms-jasmin-orchestrator` originalmente se conectaría directo al Telnet CLI (jcli) de Jasmin para administración y a su HTTP API para envío. Eso implica exponer puertos sensibles fuera del servidor y dispersar la lógica de parsing de texto jcli a lo largo del orchestrator.

Se decide separar esta responsabilidad en un servicio propio (`jasmin-admin-api`) que:
- Se comunica con Jasmin exclusivamente vía `localhost` (Telnet y HTTP)
- Expone una REST API unificada con autenticación por API Key
- El orchestrator solo conoce esta URL — nunca conecta a Jasmin directamente

Plan 007 (`007_jasmin-admin-api-spec.md`) especificó esta funcionalidad como parte del orchestrator. Este plan la extrae como servicio independiente con especificación de requisitos completa.

### Cambio de schema derivado

Se agrega a `jasmin_instances` en `sms_infrastructure`:
- `admin_api_url` — URL del sidecar para esa instancia Jasmin
- `admin_api_key` — API Key cifrada para autenticarse con el sidecar
- Columnas `api_url`, `api_username`, `api_password` marcadas como deprecated (nullable)

---

## Steps

### Fase 1 — Schema y migración

1. **Modificar `sms_infrastructure.sql`** — agregar `admin_api_url` y `admin_api_key` en `jasmin_instances`. Marcar `api_url`, `api_username`, `api_password` como deprecated (nullable). ✓ Completado 2026-05-02.

2. **Crear `008_sms_jasmin_admin_api_url.sql`** — migración idempotente para entornos existentes con instrucciones post-migración documentadas. ✓ Completado 2026-05-02.

### Fase 2 — Requisitos del servicio

3. **Definir arquitectura de despliegue**: relación 1:1 con cada instancia Jasmin. Puerto propio (sugerido: 8100). En k3s: sidecar container o Pod dedicado con ClusterIP Service. En cPanel/VPS: proceso separado en el mismo servidor.

4. **Definir gestión de sesión Telnet**: sesión persistente y única (no abrir/cerrar por request). Serialización de comandos (jcli no es concurrente). Reconexión automática con backoff exponencial. `persist` automático tras cada escritura.

5. **Implementar los 12 módulos de administración** (ver Steps detallados abajo por módulo).

6. **Implementar proxy de envío** (`/sms/send`, `/sms/send/binary`, `/sms/rate`) — proxea la HTTP API de Jasmin para que ningún puerto de Jasmin sea accesible externamente.

7. **Implementar seguridad**: autenticación por `X-API-Key` en todos los endpoints excepto `GET /health`. Credenciales Telnet y HTTP API de Jasmin en variables de entorno del sidecar, nunca expuestas.

8. **Documentar variables de entorno requeridas**: host y puerto Telnet, credenciales jcli, host y puerto HTTP API Jasmin, puerto de escucha del sidecar, API Key.

### Módulos a implementar (Paso 5)

| # | Módulo | Endpoint base | CRUD | jcli cmd |
|---|---|---|---|---|
| 1 | Grupos | `/groups` | Completo | `group` |
| 2 | Usuarios HTTP | `/users` | Completo + enable/disable | `user` |
| 3 | Conectores SMPP Outbound | `/smpp-connectors` | Completo + start/stop/status | `smppccm` |
| 4 | Conectores HTTP MO | `/http-connectors` | Completo | `httpccm` |
| 5 | Filtros | `/filters` | Completo (update = delete+add) | `filter` |
| 6 | Rutas MT | `/mt-routes` | Completo + flush | `mtrouter` |
| 7 | Rutas MO | `/mo-routes` | Completo + flush | `morouter` |
| 8 | Interceptores MT | `/mt-interceptors` | Completo + flush | `mtinterceptor` |
| 9 | Interceptores MO | `/mo-interceptors` | Completo + flush | `mointerceptor` |
| 10 | SMPP Server | `/smpp-server` | Lectura + update (singleton) | `smppserver` |
| 11 | Stats | `/stats` | Solo lectura | `stats` |
| 12 | Sistema | `/system`, `/health` | Operaciones admin | `persist`, `load` |

---

## Especificación de Módulos

### Convención de respuesta (todos los módulos)

```
Éxito con datos:   { "success": true, "data": {...} | [...] }
Éxito sin datos:   { "success": true, "message": "string" }
Error:             { "success": false, "error": "string", "detail": "string?" }
```

Códigos HTTP: `200`, `201`, `400`, `401`, `404`, `409` (ya existe), `503` (Jasmin no disponible).

---

### Módulo 1 — Grupos (`/groups`)

**jcli:** `group --list | --show -g <gid> | --add -g <gid> | --update -g <gid> | --remove -g <gid>`

| Endpoint | Método | Descripción |
|---|---|---|
| `/groups` | GET | Listar todos |
| `/groups/{gid}` | GET | Ver uno |
| `/groups` | POST | Crear |
| `/groups/{gid}` | PATCH | Actualizar |
| `/groups/{gid}` | DELETE | Eliminar |

**Campos:**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| gid | string | Sí (create) | Identificador en Jasmin. Inmutable tras crear. |
| enabled | boolean | No | Default: true. |

**Restricción:** No se puede eliminar un grupo con usuarios asignados — Jasmin rechaza el comando.

---

### Módulo 2 — Usuarios HTTP (`/users`)

**jcli:** `user --list | --show -u <uid> | --add -u <uid> -g <gid> -p <pw> | --update | --remove | --enable | --disable`

| Endpoint | Método | Descripción |
|---|---|---|
| `/users` | GET | Listar todos |
| `/users/{uid}` | GET | Ver uno |
| `/users` | POST | Crear |
| `/users/{uid}` | PATCH | Actualizar |
| `/users/{uid}` | DELETE | Eliminar |
| `/users/{uid}/status` | PATCH | Habilitar / deshabilitar |

**Campos:**

*Identidad:*
| Campo | Tipo | Req | Descripción |
|---|---|---|---|
| uid | string | Sí | ID del usuario en Jasmin. |
| gid | string | Sí | Grupo al que pertenece. |
| password | string | Sí (create) | Contraseña en texto plano. |
| enabled | boolean | No | Default: true. |

*Throughput:*
| Campo | Tipo | Descripción |
|---|---|---|
| mt_throughput | float \| null | SMS/seg MT. null = sin límite. |
| mo_throughput | float \| null | SMS/seg MO. null = sin límite. |

*Balance:*
| Campo | Tipo | Descripción |
|---|---|---|
| balance | float \| null | Crédito prepago. null/-1 = ilimitado. |
| sms_count | integer \| null | Cuota de mensajes. null = ilimitada. |

*mt_messaging_cred — Autorizaciones (booleanos, default: true):*

| Campo | Descripción |
|---|---|
| mt_auth_priority | Puede fijar prioridad del mensaje. |
| mt_auth_validity_period | Puede fijar validity period. |
| mt_auth_src_addr | Puede especificar sender ID propio. |
| mt_auth_schedule_at | Puede programar envíos a futuro. |
| mt_auth_dlr_level | Puede especificar nivel de DLR (1/2/3). |
| mt_auth_long_content | Puede enviar mensajes > 160 chars. |
| mt_allow_bulk_send | Puede usar bulk send (campañas). |

*mt_messaging_cred — Value Filters (regex \| null):*

| Campo | Descripción |
|---|---|
| mt_filter_src_addr | Regex que debe cumplir el From. null = sin restricción. |
| mt_filter_dst_addr | Regex que deben cumplir los destinos. |
| mt_filter_content | Regex que debe cumplir el contenido. |

*smpps_cred (para usuarios con acceso al SMPP Server de Jasmin):*

| Campo | Tipo | Descripción |
|---|---|---|
| smpps_allow_bind | boolean | Puede hacer bind al SMPP Server. |
| smpps_max_bindings | integer \| null | Sesiones SMPP simultáneas. null = sin límite. |
| smpps_quota_sms_count | integer \| null | Cuota SMS por sesión. null = sin límite. |
| smpps_throughput | float \| null | SMS/seg vía SMPP Server. null = sin límite. |

---

### Módulo 3 — Conectores SMPP Outbound (`/smpp-connectors`)

**jcli:** `smppccm --list | --show -c <cid> | --add -c <cid> | --update | --remove | --start | --stop`

| Endpoint | Método | Descripción |
|---|---|---|
| `/smpp-connectors` | GET | Listar todos |
| `/smpp-connectors/{cid}` | GET | Ver uno |
| `/smpp-connectors` | POST | Crear |
| `/smpp-connectors/{cid}` | PATCH | Actualizar |
| `/smpp-connectors/{cid}` | DELETE | Eliminar |
| `/smpp-connectors/{cid}/start` | POST | Iniciar conector |
| `/smpp-connectors/{cid}/stop` | POST | Detener conector |
| `/smpp-connectors/{cid}/status` | GET | Estado en tiempo real |

**Campos:**

| Campo | Tipo | Req | Descripción |
|---|---|---|---|
| cid | string | Sí | Connector ID. Inmutable. |
| host | string | Sí | Host del carrier/agregador SMPP. |
| port | integer | Sí | Puerto SMPP (típicamente 2775). |
| username | string | Sí | System ID para el bind SMPP. |
| password | string | Sí | Password del bind. |
| bind_to | enum | Sí | `transceiver` \| `transmitter` \| `receiver` |
| system_type | string | No | Tipo de sistema para el carrier (algunos lo requieren). |
| interface_version | enum | No | `33` (SMPP 3.3) \| `34` (SMPP 3.4, default). |
| address_range | string | No | Rango de números del bind (regex SMPP). |
| source_addr_ton | integer | No | Type of Number origen (0–6). |
| source_addr_npi | integer | No | Numbering Plan Indicator origen (0–9). |
| dest_addr_ton | integer | No | TON destino. |
| dest_addr_npi | integer | No | NPI destino. |
| submit_throughput | float \| null | No | SMS/seg máximo al enviar. null = sin límite. |
| dlr_expiry | integer | No | Segundos antes de expirar un DLR pendiente. |
| reconnect_on_connection_loss | boolean | No | Default: true. |
| reconnect_on_connection_loss_delay | integer | No | Segundos antes de reconectar (default: 10). |
| reconnect_on_connection_failure | boolean | No | Default: true. |
| reconnect_on_connection_failure_delay | integer | No | Segundos entre reintentos de bind (default: 10). |

**Respuesta de estado (`GET /smpp-connectors/{cid}/status`):**
```json
{
  "success": true,
  "data": {
    "cid": "string",
    "status": "started | stopped | connecting | bound",
    "sessions_count": 0,
    "last_error": "string | null"
  }
}
```

---

### Módulo 4 — Conectores HTTP para MO (`/http-connectors`)

**jcli:** `httpccm --list | --show -c <cid> | --add -c <cid> -u <url> -m <method> | --update | --remove`

Destinos donde Jasmin entrega mensajes MO (inbound) recibidos de carriers.

| Endpoint | Método | Descripción |
|---|---|---|
| `/http-connectors` | GET | Listar todos |
| `/http-connectors/{cid}` | GET | Ver uno |
| `/http-connectors` | POST | Crear |
| `/http-connectors/{cid}` | PATCH | Actualizar |
| `/http-connectors/{cid}` | DELETE | Eliminar |

**Campos:**

| Campo | Tipo | Req | Descripción |
|---|---|---|---|
| cid | string | Sí | Connector ID. Inmutable. |
| url | string | Sí | URL donde Jasmin enviará los MO SMS. |
| method | enum | Sí | `GET` \| `POST` |

---

### Módulo 5 — Filtros (`/filters`)

**jcli:** `filter --list | --show -f <fid> | --add -f <fid> -t <type> | --remove -f <fid>`

Condiciones que se asignan a rutas e interceptores.

**Nota:** `filter --update` no existe en jcli. `PATCH /filters/{fid}` debe internamente hacer delete + add + persist.

| Endpoint | Método | Descripción |
|---|---|---|
| `/filters` | GET | Listar todos |
| `/filters/{fid}` | GET | Ver uno |
| `/filters` | POST | Crear |
| `/filters/{fid}` | PATCH | Actualizar (delete + recrear internamente) |
| `/filters/{fid}` | DELETE | Eliminar |

**Tipos de filtro:**

| Tipo | Parámetros en `params` | Descripción |
|---|---|---|
| `TransparentFilter` | — | Pasa siempre. Para rutas/interceptores default. |
| `ConnectorFilter` | `connector` (cid) | Solo si el mensaje viene de ese conector. |
| `UserFilter` | `uid` | Solo si lo envía ese usuario Jasmin. |
| `GroupFilter` | `gid` | Solo si el usuario pertenece a ese grupo. |
| `SrcAddrFilter` | `regex` | El número origen debe coincidir. |
| `DstAddrFilter` | `regex` | El número destino debe coincidir. |
| `ShortMessageFilter` | `regex` | El contenido debe coincidir. |
| `DateIntervalFilter` | `before_date`, `after_date` (YYYY-MM-DD) | Rango de fechas. |
| `TimeIntervalFilter` | `before_time`, `after_time` (HH:MM) | Rango horario. |
| `DayFilter` | `days` (array entero 0–6, 0=lunes) | Días de la semana. |
| `EvalPyFilter` | `py_code` (string) | Expresión Python que retorna true/false. |
| `TagFilter` | `tag` (integer) | El mensaje debe tener ese tag asignado. |

**Body de creación:**
```json
{
  "fid": "string",
  "type": "SrcAddrFilter",
  "params": { "regex": "^52..." }
}
```

---

### Módulo 6 — Rutas MT (`/mt-routes`)

**jcli:** `mtrouter --list | --show -r <order> | --add -t <type> -r <order> -f <fids> -c <cids> | --update | --remove | --flush`

Determina por qué conector SMPP se envían los mensajes salientes (Mobile Terminated).

| Endpoint | Método | Descripción |
|---|---|---|
| `/mt-routes` | GET | Listar todas |
| `/mt-routes/{order}` | GET | Ver una |
| `/mt-routes` | POST | Crear |
| `/mt-routes/{order}` | PATCH | Actualizar |
| `/mt-routes/{order}` | DELETE | Eliminar |
| `/mt-routes/flush` | DELETE | Eliminar todas |

**Tipos de ruta MT:**

| Tipo | Conectores | Filtros | Rate |
|---|---|---|---|
| `DefaultRoute` | 1 | Ninguno | No |
| `StaticMTRoute` | 1 | 1+ | No |
| `RandomRoundrobinMTRoute` | 2+ | 1+ | No |
| `LeastCostMTRoute` | 2+ | 1+ | Sí (requerido) |

**Campos:**

| Campo | Tipo | Req | Descripción |
|---|---|---|---|
| type | enum | Sí | Tipo de ruta. |
| order | integer | Sí | Prioridad (menor = mayor). DefaultRoute: order más alto (catch-all). |
| connectors | array\<string\> | Sí | Lista de cid. |
| filters | array\<string\> | Condicional | Lista de fid. No aplica a DefaultRoute. |
| rate | float | Condicional | Costo/mensaje. Requerido para LeastCostMTRoute. |

**Regla:** Jasmin solo permite una `DefaultRoute`. Las rutas se evalúan en orden ascendente por `order`.

---

### Módulo 7 — Rutas MO (`/mo-routes`)

**jcli:** `morouter --list | --show -r <order> | --add | --update | --remove | --flush`

Determina a qué conector se entregan los mensajes entrantes (Mobile Originated).

| Endpoint | Método | Descripción |
|---|---|---|
| `/mo-routes` | GET | Listar todas |
| `/mo-routes/{order}` | GET | Ver una |
| `/mo-routes` | POST | Crear |
| `/mo-routes/{order}` | PATCH | Actualizar |
| `/mo-routes/{order}` | DELETE | Eliminar |
| `/mo-routes/flush` | DELETE | Eliminar todas |

**Tipos:** `DefaultRoute` \| `StaticMORoute`

**Campos:**

| Campo | Tipo | Req | Descripción |
|---|---|---|---|
| type | enum | Sí | Tipo de ruta. |
| order | integer | Sí | Prioridad. |
| connector | string | Sí | cid de un httpccm o smppccm. |
| filters | array\<string\> | Condicional | No aplica a DefaultRoute. |

---

### Módulo 8 — Interceptores MT (`/mt-interceptors`)

**jcli:** `mtinterceptor --list | --show -o <order> | --add -t <type> -o <order> -f <fid> -s <script> | --update | --remove | --flush`

Ejecutan scripts Python sobre el mensaje antes de enrutarlo. Permiten modificar PDUs, billing, rechazo.

| Endpoint | Método | Descripción |
|---|---|---|
| `/mt-interceptors` | GET | Listar todos |
| `/mt-interceptors/{order}` | GET | Ver uno |
| `/mt-interceptors` | POST | Crear |
| `/mt-interceptors/{order}` | PATCH | Actualizar |
| `/mt-interceptors/{order}` | DELETE | Eliminar |
| `/mt-interceptors/flush` | DELETE | Eliminar todos |

**Tipos:** `DefaultInterceptor` \| `StaticMTInterceptor`

**Campos:**

| Campo | Tipo | Req | Descripción |
|---|---|---|---|
| type | enum | Sí | Tipo. |
| order | integer | Sí | Prioridad. |
| filters | array\<string\> | Condicional | No aplica a DefaultInterceptor. |
| script | string | Sí | Código Python. Recibe `routable` con `pdu.params`. Retornar `REJECT` rechaza el mensaje. |

**Variables disponibles en el script:** `routable.source_connector`, `routable.destination_connector`, `routable.pdu` (PDU SMPP modificable: src_addr, dest_addr, short_message, priority_flag, etc.).

---

### Módulo 9 — Interceptores MO (`/mo-interceptors`)

**jcli:** `mointerceptor --list | --show -o <order> | --add | --update | --remove | --flush`

Mismo concepto que MT interceptors para mensajes entrantes.

| Endpoint | Método | Descripción |
|---|---|---|
| `/mo-interceptors` | GET | Listar todos |
| `/mo-interceptors/{order}` | GET | Ver uno |
| `/mo-interceptors` | POST | Crear |
| `/mo-interceptors/{order}` | PATCH | Actualizar |
| `/mo-interceptors/{order}` | DELETE | Eliminar |
| `/mo-interceptors/flush` | DELETE | Eliminar todos |

**Tipos:** `DefaultInterceptor` \| `StaticMOInterceptor`

Campos idénticos a MT interceptors.

---

### Módulo 10 — SMPP Server (`/smpp-server`)

**jcli:** `smppserver --list | --update`

Configuración del servidor SMPP interno de Jasmin (para resellers que conectan vía SMPP). Es un singleton — no se crea ni elimina.

| Endpoint | Método | Descripción |
|---|---|---|
| `/smpp-server` | GET | Ver configuración actual |
| `/smpp-server` | PATCH | Actualizar configuración |

**Campos actualizables:**

| Campo | Tipo | Descripción |
|---|---|---|
| host | string | IP de escucha. |
| port | integer | Puerto (default: 2775). |
| max_bindings | integer | Máximo de sesiones SMPP simultáneas. |

---

### Módulo 11 — Stats (`/stats`)

**jcli:** `stats --list | --smppccm -c <cid> | --user -u <uid>`

Solo lectura. Métricas en tiempo real. Sin operaciones de escritura ni `persist`.

| Endpoint | Método | Descripción |
|---|---|---|
| `/stats` | GET | Stats globales del gateway |
| `/stats/smpp-connectors/{cid}` | GET | Stats de un conector SMPP |
| `/stats/users/{uid}` | GET | Stats de un usuario HTTP |

**Respuesta de stats de conector:**
```json
{
  "success": true,
  "data": {
    "cid": "string",
    "status": "string",
    "sent_count": 0,
    "received_count": 0,
    "error_count": 0,
    "last_activity_at": "datetime | null"
  }
}
```

---

### Módulo 12 — Sistema (`/system`, `/health`)

| Endpoint | Método | Auth | Descripción |
|---|---|---|---|
| `/health` | GET | No | Estado del servicio y sesión Telnet. |
| `/system/persist` | POST | Sí | Ejecuta `persist` manualmente. |
| `/system/reload` | POST | Sí | Ejecuta `load` — recarga config desde disco. |
| `/system/reconnect` | POST | Sí | Fuerza reconexión de la sesión Telnet. |
| `/system/session` | GET | Sí | Info de la sesión Telnet (conectado, uptime, latencia). |

**Respuesta `/health`:**
```json
{
  "status": "ok | degraded | error",
  "telnet": { "connected": true, "uptime_seconds": 0 },
  "jasmin_http": { "reachable": true }
}
```

---

### Proxy de Envío SMS (`/sms`)

El sidecar proxea la HTTP API de Jasmin. Ningún puerto de Jasmin se expone externamente.

| Endpoint | Método | Descripción |
|---|---|---|
| `/sms/send` | POST | Enviar SMS (texto) |
| `/sms/send/binary` | POST | Enviar SMS (binario / hex-content) |
| `/sms/rate` | GET | Consultar tarifa por ruta |

**`POST /sms/send` — Campos:**

| Campo | Tipo | Req | Descripción |
|---|---|---|---|
| username | string | Sí | Usuario Jasmin HTTP (uid). |
| password | string | Sí | Contraseña del usuario. |
| to | string | Sí | Número destino E.164. |
| from | string | No | Sender ID / número origen. |
| content | string | Sí | Texto del mensaje. |
| coding | integer | No | 0=GSM7 (default), 8=UCS2, 1=binary. |
| dlr | enum | No | `yes` \| `no`. |
| dlr_url | string | No | URL para recibir el DLR. |
| dlr_level | integer | No | 1=SMSC, 2=terminal, 3=ambos. |
| dlr_method | enum | No | `GET` \| `POST`. |
| priority | integer | No | 0–3. |
| schedule_delivery_time | string | No | Timestamp SMPP para envío programado. |
| validity_period | string | No | Validez del mensaje en formato SMPP. |
| tags | array\<integer\> | No | Tags numéricos para routing/billing. |

**Respuesta exitosa:**
```json
{ "success": true, "data": { "message_id": "string" } }
```

**`GET /sms/rate` — Campos (query params):** `username`, `password`, `to`, `from`, `content`

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "rate": 0.05,
    "unit": "per_message",
    "connector_id": "string"
  }
}
```

---

## Requisitos de Sesión Telnet

- Una sesión persistente por instancia sidecar. No abrir/cerrar por cada request.
- Autenticación al conectar: esperar `Username:` → enviar user → esperar `Password:` → enviar pass → esperar `jcli>`.
- **jcli es no-concurrente**: serializar todos los comandos (cola/mutex). Dos requests simultáneos se procesan secuencialmente.
- Timeout por comando: configurable, default 10 segundos.
- Reconexión automática si la sesión cae: backoff exponencial (1s, 2s, 4s, 8s, máx 30s).
- `persist` automático tras cada operación de escritura exitosa. Si `persist` falla → retornar error al cliente (la operación se considera fallida).

---

## Seguridad

- `X-API-Key` header requerido en todos los endpoints excepto `GET /health`.
- API Key en variable de entorno del sidecar. El valor cifrado se almacena en `jasmin_instances.admin_api_key`.
- Credenciales Telnet y HTTP API de Jasmin: solo en variables de entorno del sidecar. Nunca expuestas por el API.
- Logs: método, path, status code, duración. Sin loggear passwords ni API keys.
- En k3s: Service `ClusterIP` + `NetworkPolicy` que restringe acceso al orchestrator.
- En VPS: puerto 8100 accesible solo en red privada.

---

## Files

| Archivo | Acción | Repo |
|---|---|---|
| `database/sms/sms_infrastructure.sql` | Modificar — columnas `admin_api_url`, `admin_api_key` en `jasmin_instances` | omnicanal-control-plane |
| `database/sms/008_sms_jasmin_admin_api_url.sql` | Crear — migración idempotente | omnicanal-control-plane |
| `plans/004_sms-channel/013_jasmin-admin-api.md` | Crear — este plan | omnicanal-control-plane |
| `ROADMAP.md` | Modificar — agregar entrada 013 | omnicanal-control-plane |
| Repo `jasmin-admin-api` (nuevo) | Crear — implementación del servicio | jasmin-admin-api |

---

## Dependencies

- Jasmin SMS Gateway instalado y operativo en el servidor target
- `sms_infrastructure` DB creada con schema actualizado (`sms_infrastructure.sql` + migraciones 001-008)
- Variables de entorno del sidecar configuradas antes del primer arranque
- Red privada entre el servidor Jasmin y el orchestrator

---

## Notes

### Por qué no usar `jasmin-api` (proyecto open source de jookies)
Ese proyecto es un wrapper Django/REST sobre jcli. Se descarta: hop de red extra, sin integración con schema UCaaS, sin soporte multi-tenant, mantenimiento incierto. La implementación del cliente Telnet es ~300 líneas de código controlado.

### Relación con plan 007
Plan 007 especificó esta funcionalidad como parte del `sms-jasmin-orchestrator`. Con este plan, esa funcionalidad se extrae como servicio propio. El orchestrator pasa a ser un cliente HTTP de `jasmin-admin-api`, eliminando toda lógica Telnet del orchestrator.

### filter --update no existe en jcli
Jasmin no implementa `filter --update`. El endpoint `PATCH /filters/{fid}` debe implementar internamente: `filter --remove -f <fid>` + `filter --add -f <fid> -t <type>` + params + `persist`. Si algún paso falla, se debe intentar restaurar el filtro original antes de retornar error.

---

## Execution Log

| Fecha | Paso | Resultado | Por |
|-------|------|-----------|-----|
| 2026-05-02 | Paso 1 — schema | `sms_infrastructure.sql` actualizado: columnas `admin_api_url`, `admin_api_key` agregadas; `api_url`/`api_username`/`api_password` marcadas como deprecated (nullable). | Claude |
| 2026-05-02 | Paso 2 — migración | `008_sms_jasmin_admin_api_url.sql` creado con instrucciones post-migración documentadas. | Claude |
