# Usuarios (`/users`)

## Qué son

Un usuario de Jasmin representa una **identidad de acceso al gateway**. Cada usuario tiene credenciales (uid + password), pertenece a un grupo, y lleva asociadas reglas de cuotas, throughput, autorizaciones y filtros de valor.

Los usuarios de Jasmin son distintos de los usuarios de la plataforma UCaaS. Un usuario Jasmin es la cuenta con la que un sistema (el orchestrator, una app) se autentica para **enviar mensajes MT** a través de la HTTP API de Jasmin (`POST /sms/send`), o para **conectarse como cliente SMPP** al SMPP Server de Jasmin.

---

## Lugar en el flujo

```
Cliente → POST /sms/send  (username + password del usuario Jasmin)
    → Jasmin valida credenciales
    → Jasmin verifica: ¿está el usuario habilitado?
    → Jasmin verifica: ¿está el grupo del usuario habilitado?
    → Jasmin aplica value filters del usuario
       (¿el src_addr está permitido? ¿tiene balance? ¿tiene cuota de SMS?)
    → Jasmin aplica throughput (¿superó su límite de msg/seg?)
    → Continúa con interceptores y rutas
```

El usuario es el segundo nivel de control después del grupo, y el primero que aplica reglas granulares por cuenta.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/users/` | Lista todos los usuarios |
| `GET` | `/users/{uid}` | Obtiene un usuario con todos sus parámetros |
| `POST` | `/users/` | Crea un usuario nuevo |
| `PATCH` | `/users/{uid}` | Actualiza parámetros del usuario |
| `PATCH` | `/users/{uid}/status` | Habilita o deshabilita el usuario |
| `DELETE` | `/users/{uid}` | Elimina el usuario |

---

## Parámetros

### POST `/users/` — Crear

#### Identidad (obligatorios)

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `uid` | `string` | Sí | Identificador único del usuario. Sin espacios. Inmutable. Ejemplo: `"tenant_acme_01"` |
| `gid` | `string` | Sí | Grupo al que pertenece. El grupo debe existir antes. Ejemplo: `"tenant_acme"` |
| `username` | `string` | Sí | Nombre de login para la HTTP API y SMPP bind. Sin espacios. Ejemplo: `"acme_sender"` |
| `password` | `string` | Sí | Contraseña en texto plano. Jasmin la almacena sin hash. |

> **Nota:** `uid` y `username` son conceptualmente distintos. `uid` es el identificador interno de Jasmin. `username` es el nombre de login que el sistema usa al llamar a `/sms/send`.

#### Throughput (opcionales)

Controlan cuántos mensajes por segundo puede enviar el usuario. `null` significa sin límite.

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `mt_throughput` | `float \| null` | `null` | Máx. mensajes MT por segundo vía HTTP API. Ejemplo: `10.0` |
| `mo_throughput` | `float \| null` | `null` | Máx. mensajes MO por segundo. Ejemplo: `5.0` |

#### Balance y cuotas (opcionales)

Para cuentas prepago o con cuota limitada. `null` significa ilimitado.

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `balance` | `float \| null` | `null` | Crédito prepago. Se decrementa según el `rate` de la ruta MT usada. Ejemplo: `100.0` |
| `sms_count` | `int \| null` | `null` | Cuota máxima de mensajes MT a enviar. Se decrementa con cada envío exitoso. Ejemplo: `500` |

#### Autorizaciones MT (opcionales, todos `boolean | null`)

Controlan qué campos del mensaje puede especificar el usuario al llamar a `/sms/send`. Si es `false`, Jasmin ignora ese campo aunque el cliente lo envíe. `null` usa el default de Jasmin (`true`).

| Campo | Default Jasmin | Descripción |
|-------|---------------|-------------|
| `mt_auth_priority` | `true` | Puede especificar la prioridad del mensaje (0–3) |
| `mt_auth_validity_period` | `true` | Puede especificar la vigencia del mensaje |
| `mt_auth_src_addr` | `true` | Puede especificar el sender ID (número origen o nombre alfanumérico) |
| `mt_auth_schedule_at` | `true` | Puede programar el envío a una fecha/hora futura |
| `mt_auth_dlr_level` | `true` | Puede especificar el nivel de DLR (1=SMSC, 2=terminal, 3=ambos) |
| `mt_auth_long_content` | `true` | Puede enviar mensajes de más de 160 caracteres (multipart) |

#### Value Filters MT (opcionales, `string | null`)

Expresiones regulares que el mensaje debe cumplir para ser aceptado. Si no cumple, Jasmin rechaza el envío con error. `null` significa sin restricción.

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `mt_filter_src_addr` | El sender ID debe coincidir con este regex | `"^ACME"` (solo si el from empieza con "ACME") |
| `mt_filter_dst_addr` | El número destino debe coincidir con este regex | `"^\\+?52"` (solo números mexicanos) |
| `mt_filter_content` | El texto del mensaje debe coincidir con este regex | `"^[A-Za-z0-9 ,.!?]+$"` (solo ASCII básico) |

#### SMPP Server credentials (opcionales)

Para usuarios que se conectan como clientes SMPP al SMPP Server interno de Jasmin (resellers).

| Campo | Tipo | Default Jasmin | Descripción |
|-------|------|---------------|-------------|
| `smpps_allow_bind` | `bool \| null` | `true` | Permite que este usuario haga bind al SMPP Server |
| `smpps_max_bindings` | `int \| null` | `null` | Máximo de sesiones SMPP simultáneas. `null` = sin límite |
| `smpps_quota_sms_count` | `int \| null` | `null` | Cuota de mensajes vía SMPP Server. `null` = sin límite |
| `smpps_throughput` | `float \| null` | `null` | Máx. mensajes/seg vía SMPP Server. `null` = sin límite |

---

### PATCH `/users/{uid}` — Actualizar

Todos los campos son opcionales. Solo se actualizan los campos que se envíen. Los campos no incluidos no se modifican en Jasmin.

Acepta los mismos campos que el POST, excepto `uid` (inmutable). Para cambiar `username` y `gid` también pueden incluirse.

---

### PATCH `/users/{uid}/status` — Habilitar/Deshabilitar

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `enabled` | `boolean` | Sí | `true` = habilitar, `false` = deshabilitar |

Un usuario deshabilitado no puede enviar mensajes ni hacer bind SMPP, aunque sus credenciales sean válidas.

---

### Respuesta (`UserOut`)

Incluye todos los campos configurados. Los campos no configurados en Jasmin se muestran con su valor default.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `uid` | `string` | ID del usuario |
| `gid` | `string` | Grupo al que pertenece |
| `username` | `string` | Nombre de login |
| `enabled` | `boolean` | Estado actual |
| `mt_throughput` | `float \| null` | Límite de throughput MT |
| `mo_throughput` | `float \| null` | Límite de throughput MO |
| `balance` | `float \| null` | Balance actual |
| `sms_count` | `int \| null` | Cuota actual |
| `mt_auth_*` | `boolean` | Autorizaciones MT |
| `mt_filter_*` | `string \| null` | Filtros de valor |
| `smpps_*` | varios | Credenciales SMPP Server |

> **Limitación conocida:** El campo `enabled` en la respuesta de `GET /users/{uid}` requiere una segunda llamada interna a Jasmin (`user --list`), ya que el comando `user -s {uid}` de jcli no expone el estado de habilitación. Esto es inherente al diseño de Jasmin.

---

## Ejemplos

### Crear un usuario básico

```bash
curl -X POST https://api.example.com/api/v1/users/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "tenant_acme_01",
    "gid": "tenant_acme",
    "username": "acme_sender",
    "password": "s3cur3P@ss"
  }'
```

### Crear un usuario con cuotas y límites

```bash
curl -X POST https://api.example.com/api/v1/users/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "prepaid_user_01",
    "gid": "prepaid_tier",
    "username": "prepaid01",
    "password": "pass123",
    "mt_throughput": 5.0,
    "balance": 50.0,
    "sms_count": 200,
    "mt_auth_long_content": false,
    "mt_filter_dst_addr": "^\\+?52"
  }'
```

Este usuario:
- Puede enviar hasta 5 SMS/seg
- Tiene 50 unidades de crédito (descontadas según el `rate` de la ruta)
- Tiene cuota de 200 mensajes
- No puede enviar mensajes multipart (más de 160 chars)
- Solo puede enviar a números mexicanos (`+52...`)

### Deshabilitar un usuario

```bash
curl -X PATCH https://api.example.com/api/v1/users/tenant_acme_01/status \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Recargar balance

```bash
curl -X PATCH https://api.example.com/api/v1/users/prepaid_user_01 \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"balance": 100.0}'
```

### Usar el usuario para enviar un SMS

```bash
curl -X POST https://api.example.com/api/v1/sms/send \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "acme_sender",
    "password": "s3cur3P@ss",
    "to": "+525512345678",
    "content": "Hola desde Jasmin"
  }'
```

---

## Restricciones

- **Sin espacios** en `uid`, `gid` ni `username`. Jasmin rechaza el login con error de sintaxis.
- El `uid` es **inmutable** después de creado.
- El grupo (`gid`) debe existir antes de crear el usuario.
- Jasmin almacena las contraseñas **en texto plano** internamente. Asegurar que el sidecar también use TLS/HTTPS.
- El `balance` y `sms_count` se decrementan automáticamente con cada mensaje enviado. Cuando llegan a 0, Jasmin rechaza los envíos. La API permite actualizarlos (recarga).

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | Error de Jasmin | Parámetros inválidos, grupo inexistente |
| 404 | `User '{uid}' not found` | El usuario no existe |
| 409 | `User '{uid}' already exists` | Intento de crear un uid duplicado |
| 422 | Error de validación | Espacios en uid/username, campos inválidos |
| 503 | `Jasmin is not available` | Telnet desconectado |
