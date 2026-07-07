# SMS (`/sms`)

## Qué es

El módulo SMS proporciona los endpoints para **envío de mensajes salientes** a través de Jasmin. A diferencia del resto de módulos que hablan con Jasmin vía Telnet (jcli), los endpoints de SMS se comunican directamente con la **API HTTP de Jasmin** (`/send`, `/rate`, `/balance`).

---

## Lugar en el flujo

```
Cliente → POST /sms/send (esta API)
    → API HTTP de Jasmin (localhost:1401/send)
    → Jasmin autentica usuario (username/password)
    → Jasmin ejecuta MT Interceptors
    → Jasmin evalúa MT Routes
    → Jasmin entrega al SMPP Connector
    → Carrier → SMS al destinatario
    (→ DLR callback a dlr_url si se configuró)
```

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/sms/send` | Envía un SMS de texto |
| `POST` | `/sms/send/binary` | Envía un SMS binario (contenido en hex) |
| `GET` | `/sms/rate` | Consulta el costo de enviar un SMS (sin enviarlo) |
| `GET` | `/sms/balance` | Consulta el balance y cuota de SMS de un usuario |

---

## `POST /sms/send` — Envío de texto

### Parámetros (body JSON)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `username` | `string` | Sí | UID del usuario Jasmin que realiza el envío |
| `password` | `string` | Sí | Contraseña del usuario Jasmin |
| `to` | `string` | Sí | Número destino en formato E.164. Ejemplo: `"+5215512345678"` |
| `content` | `string` | Sí | Texto del mensaje. UTF-8. Máximo 160 chars para GSM7, 70 para Unicode |
| `from` | `string \| null` | No | Sender ID o número origen. Ejemplo: `"EMPRESA"` o `"+525512345678"`. Si se omite, usa el default del carrier |
| `coding` | `int` | No | Codificación del mensaje. `0` = GSM7 (default), `8` = UCS2 (Unicode), `1` = Latin-1 |
| `dlr` | `"yes" \| "no"` | No | Solicitar reporte de entrega (DLR). Default: `"no"`. **Se ignora con `DLR_ENABLED=true`** (siempre se solicita DLR) |
| `dlr_params` | `dict \| null` | No | Params que se concatenan como query a la `DLR_URL` centralizada. Ejemplo: `{"org_id": 12}` → `DLR_URL?org_id=12`. Solo aplica con `DLR_ENABLED=true` |
| `dlr_url` | `string \| null` | No | URL de callback del DLR. **Solo modo legacy** (`DLR_ENABLED=false`); se **ignora** cuando el DLR está centralizado en el gateway |
| `dlr_level` | `int \| null` | No | Nivel de DLR: `1` = entregado al carrier, `2` = entregado al dispositivo, `3` = ambos. Default: env `DLR_LEVEL` |
| `dlr_method` | `"GET" \| "POST" \| null` | No | Método HTTP para el callback del DLR. Default: env `DLR_METHOD` |
| `priority` | `int \| null` | No | Prioridad del mensaje: `0` (normal) a `3` (máxima). Requiere autorización del usuario |
| `schedule_delivery_time` | `string \| null` | No | Programar entrega. Formato: `"YYMMDDHHmmss000+"`. Requiere autorización |
| `validity_period` | `string \| null` | No | Período de validez. Formato relativo: `"000024000000R"` (24 horas) |
| `tags` | `list[int]` | No | Tags numéricos para el mensaje, usados por `TagFilter`. Ejemplo: `[99, 200]` |

### Respuesta (`SmsSendOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `message_id` | `string` | ID único del mensaje asignado por Jasmin. Úsalo para correlacionar el DLR |

### Ejemplo

```bash
curl -X POST https://api.example.com/api/v1/sms/send \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tenant_acme",
    "password": "secret",
    "to": "+5215512345678",
    "content": "Tu código de verificación es: 482910",
    "from": "ACME",
    "coding": 0,
    "dlr": "yes",
    "dlr_url": "https://myapp.com/dlr/callback",
    "dlr_level": 2,
    "dlr_method": "POST"
  }'
```

Respuesta:
```json
{
  "data": {
    "message_id": "7e3d8f2a-1b4c-4d6e-9f0a"
  }
}
```

---

## `POST /sms/send/binary` — Envío binario

Envía un mensaje con contenido binario arbitrario, útil para WAP push, ringtones, o mensajes propietarios.

### Parámetros (body JSON)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `username` | `string` | Sí | UID del usuario Jasmin |
| `password` | `string` | Sí | Contraseña |
| `to` | `string` | Sí | Número destino E.164 |
| `hex_content` | `string` | Sí | Contenido del mensaje en hexadecimal. Ejemplo: `"48656c6c6f"` (= "Hello") |
| `coding` | `int` | No | Data coding del PDU SMPP. Default: `1` (binary/8-bit) |
| `from` | `string \| null` | No | Sender ID o número origen |
| `dlr` | `"yes" \| "no"` | No | Solicitar DLR |
| `dlr_url` | `string \| null` | No | URL de callback DLR |
| `dlr_level` | `int \| null` | No | Nivel de DLR |
| `dlr_method` | `"GET" \| "POST" \| null` | No | Método HTTP del DLR |

---

## `GET /sms/rate` — Consultar tarifa

Consulta cuánto costaría enviar un SMS a un número específico con las rutas MT actuales, **sin enviarlo realmente**.

### Parámetros (query string)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `username` | `string` | Sí | UID del usuario Jasmin |
| `password` | `string` | Sí | Contraseña |
| `to` | `string` | Sí | Número destino (para evaluar qué ruta aplica) |
| `from` | `string \| null` | No | Número origen (para evaluación de filtros) |
| `content` | `string \| null` | No | Contenido del mensaje (para filtros de contenido) |

### Respuesta (`SmsRateOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `rate` | `float` | Costo por mensaje en unidades de balance. `0.0` = gratis |
| `unit` | `string` | Siempre `"per_message"` |
| `connector_id` | `string \| null` | ID del conector SMPP que se usaría para ese destino |

### Ejemplo

```bash
curl "https://api.example.com/api/v1/sms/rate?username=tenant_acme&password=secret&to=%2B5215512345678" \
  -H "X-API-Key: tu-api-key"
```

---

## `GET /sms/balance` — Consultar balance

Consulta el balance disponible y la cuota de SMS de un usuario Jasmin.

### Parámetros (query string)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `username` | `string` | Sí | UID del usuario Jasmin |
| `password` | `string` | Sí | Contraseña |

### Respuesta (`SmsBalanceOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `balance` | `float \| null` | Balance disponible. `null` = ilimitado (configuración UD en Jasmin) |
| `sms_count` | `int \| null` | Cuota de SMS disponible. `null` = ilimitado |

### Ejemplo

```bash
curl "https://api.example.com/api/v1/sms/balance?username=tenant_acme&password=secret" \
  -H "X-API-Key: tu-api-key"
```

Respuesta:
```json
{
  "data": {
    "balance": 47.50,
    "sms_count": null
  }
}
```

---

## DLR (Delivery Receipt) — Callback de entrega

Cuando se envía un mensaje con `dlr = "yes"`, Jasmin hace una llamada HTTP a la URL del DLR cuando el carrier confirma la entrega.

### DLR centralizado (recomendado)

Con `DLR_ENABLED=true`, la URL del DLR se define **en el gateway** vía variables de entorno, no la manda el cliente. Esto centraliza el punto de recepción, elimina el riesgo de SSRF (el cliente no puede apuntar a URLs internas) y da un formato consistente. En este modo **todos los envíos solicitan DLR**: el campo `dlr` del body se ignora.

| Variable | Descripción |
|----------|-------------|
| `DLR_ENABLED` | Activa el DLR centralizado (`true`/`false`) |
| `DLR_URL` | URL base del webhook que recibe los DLR |
| `DLR_METHOD` | `GET` o `POST` (dlr-method hacia Jasmin). Default `POST` |
| `DLR_LEVEL` | `1`/`2`/`3`. Default `3` |
| `DLR_DEFAULT_PARAMS` | JSON dict de params fijos que se concatenan siempre. Opcional |

El cliente aporta en el body `dlr_params` (dict), que se **concatenan como query params** a `DLR_URL`:

```
DLR_URL = https://host/api/v1/sms/webhook/dlr
body    = { "dlr": "yes", "dlr_params": { "org_id": 12, "ref": "abc" } }
→ dlr-url que recibe Jasmin: https://host/api/v1/sms/webhook/dlr?org_id=12&ref=abc
```

Jasmin **preserva ese query string** y le añade sus propios campos al hacer el callback. Si `DLR_METHOD=POST`, los campos de Jasmin viajan en el body `form-urlencoded` y tus `dlr_params` siguen en el query string (los `dlr_params` **no** pueden ir en el body: Jasmin es dueño del body). Si `DLR_METHOD=GET`, todo viaja en el query string.

> **Nota:** como los `dlr_params` viajan en la URL, se recomienda mantenerlos cortos (identificadores como `org_id`, `ref`), no payloads grandes.

### Parámetros que Jasmin incluye en el callback

| Parámetro | Descripción |
|-----------|-------------|
| `id` | Message ID del SMS (el mismo que retorna `/send`) |
| `sub` | Número de partes del mensaje (1 para mensajes cortos) |
| `dlvrd` | Mensajes entregados |
| `submit date` | Fecha/hora de envío |
| `done date` | Fecha/hora de entrega |
| `stat` | Estado: `DELIVRD` (entregado), `UNDELIV` (no entregado), `EXPIRED`, etc. |
| `err` | Código de error del carrier (0 = sin error) |
| `text` | Primeros caracteres del mensaje |

### Niveles de DLR

| `dlr_level` | Cuándo dispara el callback |
|-------------|---------------------------|
| `1` | Solo cuando el carrier acepta el mensaje |
| `2` | Solo cuando el mensaje llega al dispositivo |
| `3` | En ambos eventos |

---

## Codificaciones (`coding`)

| Valor | Nombre | Uso |
|-------|--------|-----|
| `0` | GSM7 | Texto estándar: 160 chars por SMS, caracteres del alfabeto GSM |
| `1` | Latin-1 / Binary | Para SMS binarios o contenido Latin-1 |
| `8` | UCS2 / Unicode | Emojis, chino, árabe, etc.: 70 chars por SMS |

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | `Jasmin rejected the message: ...` | Error genérico de Jasmin (ver detalle en respuesta) |
| 403 | `Authentication failed or user quota exceeded` | Credenciales inválidas, usuario deshabilitado o sin balance |
| 422 | `No route found for the message` | No hay ruta MT que coincida con ese destino/usuario |
| 503 | `Cannot reach Jasmin HTTP API` | El servicio HTTP de Jasmin no está disponible |

---

## Prerequisitos para enviar

Para que el envío funcione, deben existir previamente:

1. **Usuario** (`POST /users/`) con las credenciales que se usan en `username`/`password`
2. **Conector SMPP** (`POST /smpp-connectors/`) iniciado y conectado al carrier
3. **Ruta MT** (`POST /mt-routes/`) que apunte el tráfico del usuario al conector
4. (Opcional) **Balance** suficiente si las rutas tienen `rate > 0`
