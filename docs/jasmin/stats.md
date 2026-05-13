# Estadísticas (`/stats`)

## Qué son

El módulo de estadísticas expone métricas en tiempo real que Jasmin recopila internamente. No requiere configuración previa — Jasmin comienza a acumular contadores desde que arranca.

Las estadísticas son **acumulativas**: no se resetean entre llamadas a la API. Están disponibles para:
- Todos los conectores SMPP (salientes)
- Todos los usuarios Jasmin
- La API HTTP de Jasmin (endpoint `/send`)
- La API SMPP Server de Jasmin (inbound bindings)

---

## Lugar en el flujo

```
Jasmin (runtime)
  ├── SMPP Connectors → stats --smppcs / stats --smppc=CID
  ├── Users           → stats --users  / stats --user=UID
  ├── HTTP API        → stats --httpapi    (POST /send del cliente)
  └── SMPP Server API → stats --smppsapi   (bindings entrantes)
```

Las estadísticas son de **solo lectura** — no existe un endpoint para resetearlas ni modificarlas.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/stats/` | Resumen global: todos los conectores, usuarios, HTTP API y SMPP Server API |
| `GET` | `/stats/smpp-connectors/{cid}` | Estadísticas detalladas de un conector SMPP específico |
| `GET` | `/stats/users/{uid}` | Estadísticas detalladas de un usuario Jasmin específico |
| `GET` | `/stats/http-api` | Estadísticas de la API HTTP de Jasmin |
| `GET` | `/stats/smpp-server-api` | Estadísticas del servidor SMPP de Jasmin (inbound) |

---

## Respuestas

### `GET /stats/` — Resumen global (`GlobalStatsOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `smpp_connectors` | `list[SmppConnectorStatsSummary]` | Una fila por conector: CID, fechas de conexión, submits, delivers, errores |
| `users` | `list[UserStatsSummary]` | Una fila por usuario: UID, conexiones SMPP bound, requests HTTP |
| `http_api` | `HttpApiStatsOut` | Métricas de la API HTTP de Jasmin |
| `smpp_server_api` | `SmppServerApiStatsOut` | Métricas del servidor SMPP de Jasmin |

### `SmppConnectorStatsSummary` (fila de resumen)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cid` | `string` | ID del conector SMPP |
| `connected_at` | `string \| null` | Última vez que se conectó (ND si nunca) |
| `bound_at` | `string \| null` | Última vez que hizo bind |
| `disconnected_at` | `string \| null` | Última desconexión |
| `submits` | `string` | Formato `"enviados/intentados"` — e.g. `"150/160"` |
| `delivers` | `string` | Formato `"entregados/intentados"` |
| `qos_errors` | `int` | Errores de calidad de servicio (throttling) |
| `other_errors` | `int` | Otros errores de submit |

### `UserStatsSummary` (fila de resumen)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `uid` | `string` | ID del usuario |
| `smpp_bound_connections` | `int` | Conexiones SMPP actualmente bound |
| `smpp_last_activity` | `string \| null` | Última actividad SMPP |
| `http_request_count` | `int` | Total de requests HTTP enviados |
| `http_last_activity` | `string \| null` | Última actividad HTTP |

---

### `GET /stats/smpp-connectors/{cid}` — Detalle de conector (`SmppConnectorStatsOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cid` | `string` | ID del conector |
| `created_at` | `string \| null` | Cuándo se creó el registro de stats (al arrancar Jasmin) |
| `connected_at` | `string \| null` | Última conexión TCP al carrier |
| `bound_at` | `string \| null` | Último bind SMPP exitoso |
| `disconnected_at` | `string \| null` | Última desconexión |
| `last_received_pdu_at` | `string \| null` | Último PDU recibido del carrier |
| `last_sent_pdu_at` | `string \| null` | Último PDU enviado al carrier |
| `connected_count` | `int` | Número total de conexiones TCP desde que arrancó Jasmin |
| `bound_count` | `int` | Número total de binds exitosos |
| `disconnected_count` | `int` | Número total de desconexiones |
| `submit_sm_request_count` | `int` | Mensajes enviados a este conector para despacho |
| `submit_sm_count` | `int` | Mensajes aceptados por el carrier (submit_sm_resp OK) |
| `deliver_sm_count` | `int` | MO recibidos del carrier |
| `elink_count` | `int` | Enquire links intercambiados |
| `throttling_error_count` | `int` | Errores de throttling del carrier |
| `other_submit_error_count` | `int` | Otros errores en submit_sm |
| `interceptor_error_count` | `int` | Errores en scripts de interceptor MT |
| `interceptor_count` | `int` | Veces que se ejecutó un interceptor MT |

---

### `GET /stats/users/{uid}` — Detalle de usuario (`UserStatsOut`)

El detalle de usuario está dividido en dos secciones: estadísticas del **SMPP Server** (conexiones entrantes que el usuario hace como cliente SMPP) y estadísticas de la **HTTP API** (requests HTTP al endpoint `/send`).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `smpp_bind_count` | `int` | Total de binds SMPP del usuario |
| `smpp_unbind_count` | `int` | Total de unbinds SMPP |
| `smpp_bound_connections` | `int` | Conexiones actualmente bound (suma de tx/rx/trx) |
| `smpp_submit_sm_request_count` | `int` | Submit SM enviados vía SMPP |
| `smpp_submit_sm_count` | `int` | Submit SM aceptados por Jasmin vía SMPP |
| `smpp_deliver_sm_count` | `int` | Deliver SM recibidos vía SMPP |
| `smpp_elink_count` | `int` | Enquire links intercambiados |
| `smpp_throttling_error_count` | `int` | Errores de throttling |
| `smpp_other_submit_error_count` | `int` | Otros errores SMPP |
| `smpp_last_activity_at` | `string \| null` | Última actividad SMPP |
| `http_connects_count` | `int` | Número de requests HTTP al endpoint `/send` |
| `http_submit_sm_request_count` | `int` | Submit SM enviados vía HTTP API |
| `http_balance_request_count` | `int` | Consultas de balance `/sms/balance` |
| `http_rate_request_count` | `int` | Consultas de tarifa `/sms/rate` |
| `http_last_activity_at` | `string \| null` | Última actividad HTTP |

---

### `GET /stats/http-api` — HTTP API (`HttpApiStatsOut`)

Métricas globales de la API HTTP de Jasmin (el endpoint `/send` que recibe los SMS salientes).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `created_at` | `string \| null` | Cuándo comenzó a acumularse (al arrancar Jasmin) |
| `last_request_at` | `string \| null` | Último request recibido |
| `last_success_at` | `string \| null` | Último SMS enviado con éxito |
| `request_count` | `int` | Total de requests recibidos |
| `success_count` | `int` | Requests que resultaron en un SMS enviado |
| `auth_error_count` | `int` | Rechazos por credenciales inválidas |
| `route_error_count` | `int` | Rechazos por sin ruta MT disponible |
| `interceptor_error_count` | `int` | Rechazos por error en interceptor MT |
| `interceptor_count` | `int` | Veces que se ejecutó un interceptor |
| `throughput_error_count` | `int` | Rechazos por límite de throughput del usuario |
| `charging_error_count` | `int` | Rechazos por balance insuficiente |
| `server_error_count` | `int` | Errores internos de Jasmin |

---

### `GET /stats/smpp-server-api` — SMPP Server API (`SmppServerApiStatsOut`)

Métricas del servidor SMPP de Jasmin — el servidor al que los clientes externos se conectan usando el protocolo SMPP.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `created_at` | `string \| null` | Cuándo comenzó a acumularse |
| `last_received_pdu_at` | `string \| null` | Último PDU recibido de un cliente SMPP externo |
| `last_sent_pdu_at` | `string \| null` | Último PDU enviado a un cliente SMPP externo |
| `connected_count` | `int` | Conexiones TCP actualmente activas |
| `connect_count` | `int` | Total histórico de conexiones TCP |
| `disconnect_count` | `int` | Total histórico de desconexiones |
| `bound_trx_count` | `int` | Clientes actualmente bound en modo transceiver |
| `bound_rx_count` | `int` | Clientes actualmente bound en modo receiver |
| `bound_tx_count` | `int` | Clientes actualmente bound en modo transmitter |
| `bind_trx_count` | `int` | Total histórico de binds transceiver |
| `bind_rx_count` | `int` | Total histórico de binds receiver |
| `bind_tx_count` | `int` | Total histórico de binds transmitter |
| `unbind_count` | `int` | Total histórico de unbinds |
| `submit_sm_request_count` | `int` | Submit SM recibidos de clientes externos |
| `submit_sm_count` | `int` | Submit SM procesados |
| `deliver_sm_count` | `int` | Deliver SM enviados a clientes externos (MO) |
| `elink_count` | `int` | Enquire links intercambiados |
| `throttling_error_count` | `int` | Errores de throttling |
| `other_submit_error_count` | `int` | Otros errores de submit |
| `interceptor_error_count` | `int` | Errores en interceptores |
| `interceptor_count` | `int` | Ejecuciones de interceptores |

---

## Ejemplos

### Resumen global del sistema

```bash
curl https://api.example.com/api/v1/stats/ \
  -H "X-API-Key: tu-api-key"
```

### Estadísticas de un conector SMPP

```bash
curl https://api.example.com/api/v1/stats/smpp-connectors/carrier_mx \
  -H "X-API-Key: tu-api-key"
```

### Estadísticas de un usuario

```bash
curl https://api.example.com/api/v1/stats/users/tenant_acme_01 \
  -H "X-API-Key: tu-api-key"
```

### Solo métricas HTTP

```bash
curl https://api.example.com/api/v1/stats/http-api \
  -H "X-API-Key: tu-api-key"
```

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 404 | `Stats for connector '{cid}' not found` | El CID no existe o Jasmin no tiene stats para ese conector |
| 404 | `Stats for user '{uid}' not found` | El UID no existe en Jasmin |
| 503 | `Jasmin is not available` | Telnet desconectado |

---

## Consideraciones

- Las estadísticas **se resetean al reiniciar Jasmin**. No persisten entre reinicios.
- `null` en timestamps significa que el evento nunca ha ocurrido (Jasmin retorna `ND` = No Data).
- El campo `submits` en el resumen tiene formato `"enviados/intentados"` — indica cuántos de los mensajes intentados lograron ser aceptados por el carrier.
- Los contadores de interceptores reflejan todas las ejecuciones, incluso las que no modificaron el mensaje.
