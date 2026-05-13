# Conectores HTTP (`/http-connectors`)

## Qué son

Un conector HTTP (`httpccm` en jcli) define un **destino web al que Jasmin entrega los mensajes MO** (Mobile Originated — mensajes que envían usuarios finales desde su celular hacia el sistema).

Cuando Jasmin recibe un mensaje MO desde un carrier (vía SMPP), evalúa las rutas MO para determinar a qué conector entregarlo. Si la ruta ganadora apunta a un conector HTTP, Jasmin hace una llamada GET o POST a la URL configurada, enviando los datos del mensaje como parámetros.

Los conectores HTTP son, en esencia, **webhooks de entrega de mensajes entrantes**.

---

## Lugar en el flujo

```
Usuario final → envía SMS al número del carrier
    → Carrier entrega el MO al SMPP bind de Jasmin
    → Jasmin evalúa MO Interceptors
    → Jasmin evalúa MO Routes
    → Ruta ganadora apunta a un HTTP Connector
    → Jasmin hace GET/POST a la URL del conector
         con: from, to, content, message_id, etc.
    → La aplicación receptora procesa el mensaje
```

---

## Qué datos envía Jasmin al conector HTTP

Jasmin pasa los siguientes parámetros al hacer la llamada a la URL del conector:

| Parámetro | Descripción |
|-----------|-------------|
| `from` | Número del remitente (quien envió el SMS) |
| `to` | Número destino (el número configurado en el sistema) |
| `content` | Texto del mensaje |
| `message-id` | ID del mensaje asignado por Jasmin |
| `priority` | Prioridad del mensaje |
| `coding` | Codificación del mensaje (0=GSM7, 8=UCS2) |

Con método `GET`: estos parámetros van en la query string.
Con método `POST`: van en el body como form data (`application/x-www-form-urlencoded`).

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/http-connectors/` | Lista todos los conectores HTTP |
| `GET` | `/http-connectors/{cid}` | Obtiene la configuración de un conector |
| `POST` | `/http-connectors/` | Crea un conector nuevo |
| `PATCH` | `/http-connectors/{cid}` | Actualiza la URL o el método |
| `DELETE` | `/http-connectors/{cid}` | Elimina el conector |

---

## Parámetros

### POST `/http-connectors/` — Crear

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `cid` | `string` | Sí | Identificador único del conector. Usado en rutas MO con prefijo `http(cid)`. Inmutable. Ejemplo: `"webhook_crm"` |
| `url` | `string` | Sí | URL completa que recibirá el mensaje. Debe ser accesible desde el servidor de Jasmin. Ejemplo: `"https://myapp.com/sms/inbound"` |
| `method` | `string` | Sí | Método HTTP. Solo `"GET"` o `"POST"`. |

### PATCH `/http-connectors/{cid}` — Actualizar

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `url` | `string \| null` | No | Nueva URL de entrega |
| `method` | `string \| null` | No | Nuevo método HTTP (`"GET"` o `"POST"`) |

### Respuesta (`HttpConnectorOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cid` | `string` | ID del conector |
| `url` | `string` | URL configurada |
| `method` | `string` | Método HTTP |

---

## Cuándo usar GET vs POST

| Método | Cuándo usarlo |
|--------|---------------|
| `GET` | URLs simples, servicios que solo leen parámetros en query string. Útil para integraciones legacy o pruebas rápidas. |
| `POST` | Preferido para producción. Más seguro para payloads con caracteres especiales en el contenido del SMS. El body no queda en logs de servidor como lo hace la query string. |

---

## Ejemplos

### Crear un conector para un webhook de CRM

```bash
curl -X POST https://api.example.com/api/v1/http-connectors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cid": "crm_webhook",
    "url": "https://crm.empresa.com/api/sms/inbound",
    "method": "POST"
  }'
```

### Crear un conector de prueba (GET)

```bash
curl -X POST https://api.example.com/api/v1/http-connectors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cid": "test_listener",
    "url": "https://webhook.site/tu-uuid",
    "method": "GET"
  }'
```

### Actualizar la URL

```bash
curl -X PATCH https://api.example.com/api/v1/http-connectors/crm_webhook \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://crm.empresa.com/api/v2/sms/inbound"}'
```

### Eliminar

```bash
curl -X DELETE https://api.example.com/api/v1/http-connectors/test_listener \
  -H "X-API-Key: tu-api-key"
```

---

## Lo que Jasmin envía a la URL

Ejemplo de lo que recibe el servidor cuando `method = "POST"`:

```
POST https://crm.empresa.com/api/sms/inbound
Content-Type: application/x-www-form-urlencoded

from=%2B525512345678&to=%2B525500000001&content=Quiero+informacion&message-id=abc123&priority=0&coding=0
```

El servidor receptor debe responder con HTTP 200 para que Jasmin considere la entrega exitosa. Si responde con otro código, Jasmin puede reintentar (según su configuración interna).

---

## Restricciones

- La URL debe ser accesible desde el servidor donde corre Jasmin. Si el servidor está en una red privada y la URL es un servicio externo, verificar que haya conectividad de salida.
- Jasmin no realiza autenticación al llamar a la URL. Si el endpoint necesita autenticación, una opción es incluirla en la URL como query param (ej: `?token=...`) o usar un proxy que añada headers.
- El `cid` no puede modificarse después de creado.
- No hay endpoint de start/stop para conectores HTTP. No tienen estado de conexión — Jasmin llama a la URL cada vez que llega un MO que coincide con la ruta.

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 404 | `Connector '{cid}' not found` | El conector no existe |
| 409 | `Connector '{cid}' already exists` | CID duplicado |
| 503 | `Jasmin is not available` | Telnet desconectado |
