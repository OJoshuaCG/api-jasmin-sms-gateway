# Conectores SMPP (`/smpp-connectors`)

## Qué son

Un conector SMPP (también llamado SMPP outbound connector o `smppccm` en jcli) representa una **conexión TCP de Jasmin hacia un SMSC** (Short Message Service Centre) externo, que es el sistema del carrier o agregador que entrega los SMS al usuario final.

Jasmin actúa como ESME (External Short Message Entity) y establece una sesión SMPP con el SMSC del carrier. Por esta conexión viajan los mensajes MT (salientes) que el sistema envía.

Un conector SMPP debe **iniciarse** (`start`) para que Jasmin establezca la conexión. Hasta que está activo y en estado `bound`, los mensajes enrutados a él no pueden ser enviados.

---

## Lugar en el flujo

```
POST /sms/send
    → Jasmin evalúa rutas MT
    → Ruta ganadora apunta a un SMPP Connector
    → Jasmin envía el PDU submit_sm por esa conexión SMPP
    → SMSC del carrier recibe el mensaje
    → SMSC retorna submit_sm_resp con un message_id
    → (Asíncrono) SMSC envía deliver_sm con el DLR
```

El conector SMPP es el **canal de salida** de Jasmin. Sin al menos un conector iniciado y en estado bound, ningún mensaje MT puede ser entregado al carrier.

---

## Ciclo de vida de un conector

```
Creado (stopped)
    │
    ▼ POST /{cid}/start
Conectando (connecting)
    │
    ▼ (handshake SMPP exitoso)
Activo (bound_TRX / bound_TX / bound_RX)
    │
    ▼ POST /{cid}/stop   (o pérdida de conexión)
Detenido (stopped)
```

Si la conexión se cae y `reconnect_on_connection_loss = true`, el conector intenta reconectar automáticamente.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/smpp-connectors/` | Lista todos los conectores con su configuración |
| `GET` | `/smpp-connectors/{cid}` | Obtiene la configuración de un conector |
| `POST` | `/smpp-connectors/` | Crea un conector nuevo |
| `PATCH` | `/smpp-connectors/{cid}` | Actualiza la configuración |
| `DELETE` | `/smpp-connectors/{cid}` | Elimina el conector |
| `POST` | `/smpp-connectors/{cid}/start` | Inicia la conexión SMPP |
| `POST` | `/smpp-connectors/{cid}/stop` | Detiene la conexión SMPP |
| `GET` | `/smpp-connectors/{cid}/status` | Estado en tiempo real de la conexión |

---

## Parámetros

### POST `/smpp-connectors/` — Crear

#### Identificación y conexión (obligatorios)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `cid` | `string` | Sí | Identificador único del conector. Usado en rutas MT con prefijo `smppc(cid)`. Inmutable. Ejemplo: `"carrier_mx"` |
| `host` | `string` | Sí | Hostname o IP del SMSC del carrier. Ejemplo: `"smpp.carrier.com"` |
| `port` | `int` | Sí | Puerto TCP. El estándar SMPP es 2775. Rango: 1–65535. |
| `username` | `string` | Sí | `system_id` SMPP para la autenticación del bind. Máx. 15 chars (límite del protocolo SMPP 3.4). |
| `password` | `string` | Sí | Password del bind SMPP. Máx. 8 chars (límite del protocolo SMPP 3.4). |

#### Modo de bind (opcional)

| Campo | Tipo | Default | Valores | Descripción |
|-------|------|---------|---------|-------------|
| `bind_to` | `string` | `"transceiver"` | `"transceiver"` `"transmitter"` `"receiver"` | Tipo de sesión SMPP. `transceiver` permite enviar y recibir (recomendado). `transmitter` solo enviar. `receiver` solo recibir DLR/MO. |

#### Parámetros de protocolo (opcionales)

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `system_type` | `string \| null` | `null` | Campo `system_type` del PDU bind. Algunos carriers lo requieren (ej: `"OTA"`, `"VMS"`). Máx. 12 chars. |
| `interface_version` | `string` | `"34"` | Versión del protocolo SMPP. `"34"` = SMPP 3.4 (recomendado). `"33"` = SMPP 3.3 (algunos carriers legacy). |
| `address_range` | `string \| null` | `null` | Rango de direcciones del bind (campo `address_range` del PDU). Carriers específicos lo requieren. Máx. 40 chars. |

#### TON y NPI (opcionales)

TON (Type of Number) y NPI (Numbering Plan Indicator) controlan cómo se interpretan los números en el SMSC. Jasmin los usa para todos los mensajes enviados por este conector. Si el carrier no requiere un valor específico, dejar en `null`.

**TON — valores posibles:**

| Valor | Significado | Uso típico |
|-------|-------------|------------|
| `0` | Unknown | Genérico cuando no se sabe |
| `1` | International | Números E.164 con código de país (`+521234567890`) |
| `2` | National | Números sin código de país |
| `5` | Alphanumeric | Sender IDs de texto (`"ACME"`) |
| `6` | Abbreviated | Números cortos |

**NPI — valores posibles:**

| Valor | Significado |
|-------|-------------|
| `0` | Unknown |
| `1` | ISDN/E.164 (el más común para números celulares) |
| `8` | National |
| `9` | Private |

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `source_addr_ton` | `int \| null` | `null` | TON del número origen (sender ID). Rango: 0–6. |
| `source_addr_npi` | `int \| null` | `null` | NPI del número origen. Rango: 0–18. |
| `dest_addr_ton` | `int \| null` | `null` | TON del número destino. Rango: 0–6. |
| `dest_addr_npi` | `int \| null` | `null` | NPI del número destino. Rango: 0–18. |

#### Throughput y DLR (opcionales)

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `submit_throughput` | `float \| null` | `null` | Máximo de PDUs `submit_sm` por segundo que Jasmin envía a este SMSC. `null` = sin límite. Ejemplo: `50.0` |
| `dlr_expiry` | `int \| null` | `null` | Segundos que Jasmin espera el DLR (`deliver_sm`) antes de marcarlo como expirado. `null` = usa el default de Jasmin. Ejemplo: `86400` (24 horas) |

#### Reconexión automática (opcionales)

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `reconnect_on_connection_loss` | `bool \| null` | `true` | Si la sesión activa se cae, Jasmin intenta reconectar automáticamente. |
| `reconnect_on_connection_loss_delay` | `int \| null` | `10` | Segundos de espera antes de cada intento de reconexión tras pérdida de sesión. |
| `reconnect_on_connection_failure` | `bool \| null` | `true` | Si el intento de bind inicial falla, Jasmin reintenta. |
| `reconnect_on_connection_failure_delay` | `int \| null` | `10` | Segundos entre reintentos de bind fallido. |

---

### PATCH `/smpp-connectors/{cid}` — Actualizar

Todos los campos son opcionales. Solo se actualizan los enviados. El `cid` no puede cambiarse.

> **Nota:** Actualizar un conector que está activo requiere detenerlo y reiniciarlo para que los cambios surtan efecto. La actualización modifica la configuración en memoria/disco pero no interrumpe la sesión SMPP activa.

---

### GET `/smpp-connectors/{cid}/status` — Estado

Respuesta:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cid` | `string` | ID del conector |
| `status` | `string` | Estado actual: `stopped`, `started`, `connecting`, `bound_TRX`, `bound_TX`, `bound_RX` |
| `sessions_count` | `int` | Número de sesiones SMPP activas |
| `last_error` | `string \| null` | Último error de conexión, si existe |

---

## Ejemplos

### Crear un conector para un carrier estándar

```bash
curl -X POST https://api.example.com/api/v1/smpp-connectors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cid": "carrier_mx",
    "host": "smpp.carrier.com.mx",
    "port": 2775,
    "username": "mycompany",
    "password": "smppP@ss",
    "bind_to": "transceiver",
    "submit_throughput": 50.0,
    "dlr_expiry": 86400,
    "source_addr_ton": 1,
    "source_addr_npi": 1,
    "dest_addr_ton": 1,
    "dest_addr_npi": 1
  }'
```

### Iniciar el conector

```bash
curl -X POST https://api.example.com/api/v1/smpp-connectors/carrier_mx/start \
  -H "X-API-Key: tu-api-key"
```

### Verificar que está conectado

```bash
curl https://api.example.com/api/v1/smpp-connectors/carrier_mx/status \
  -H "X-API-Key: tu-api-key"
```

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

### Actualizar el throughput

```bash
curl -X PATCH https://api.example.com/api/v1/smpp-connectors/carrier_mx \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"submit_throughput": 100.0}'
```

### Detener y eliminar

```bash
curl -X POST https://api.example.com/api/v1/smpp-connectors/carrier_mx/stop \
  -H "X-API-Key: tu-api-key"

curl -X DELETE https://api.example.com/api/v1/smpp-connectors/carrier_mx \
  -H "X-API-Key: tu-api-key"
```

---

## Estados posibles del conector

| Estado | Significado |
|--------|-------------|
| `stopped` | Conector creado pero no iniciado, o detenido manualmente |
| `started` | Jasmin intentando conectar (en proceso de bind) |
| `connecting` | TCP conectado, bind SMPP en progreso |
| `bound_TRX` | Bind transceiver activo — puede enviar y recibir |
| `bound_TX` | Bind transmitter activo — solo envío |
| `bound_RX` | Bind receiver activo — solo recepción |

Para que los mensajes MT fluyan, el conector debe estar en `bound_TRX` o `bound_TX`.

---

## Configuración típica por escenario

### Carrier con sender ID alfanumérico

```json
{
  "source_addr_ton": 5,
  "source_addr_npi": 0
}
```

### Carrier con números E.164 internacionales

```json
{
  "source_addr_ton": 1,
  "source_addr_npi": 1,
  "dest_addr_ton": 1,
  "dest_addr_npi": 1
}
```

### Carrier legacy con reconexión agresiva

```json
{
  "interface_version": "33",
  "reconnect_on_connection_loss": true,
  "reconnect_on_connection_loss_delay": 5,
  "reconnect_on_connection_failure": true,
  "reconnect_on_connection_failure_delay": 5
}
```

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | Error de Jasmin | Parámetros inválidos |
| 404 | `Connector '{cid}' not found` | El conector no existe |
| 409 | `Connector '{cid}' already exists` | CID duplicado |
| 503 | `Jasmin is not available` | Telnet desconectado |
