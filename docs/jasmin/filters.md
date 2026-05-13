# Filtros (`/filters`)

## Qué son

Un filtro es una **condición que Jasmin evalúa sobre un mensaje** para decidir si ese mensaje "coincide" con una regla determinada. Los filtros no actúan solos; se asignan a rutas e interceptores para determinar cuándo aplican.

Cuando Jasmin evalúa una ruta o interceptor, verifica si **todos los filtros** asignados a esa ruta/interceptor coinciden con el mensaje. Si todos coinciden, la ruta/interceptor aplica. Si al menos uno no coincide, Jasmin pasa a evaluar la siguiente ruta/interceptor en orden.

Un filtro puede reutilizarse en múltiples rutas e interceptores simultáneamente.

---

## Lugar en el flujo

```
Mensaje entra a Jasmin (MT o MO)
    │
    ▼ (para cada ruta/interceptor, en orden ascendente)
    
    Ruta con filtros [filtro_A, filtro_B]
        → ¿coincide filtro_A con el mensaje?  No → siguiente ruta
        → ¿coincide filtro_B con el mensaje?  No → siguiente ruta
        → Todos coinciden → esta ruta aplica → se usa su conector
```

Un `TransparentFilter` siempre coincide — es el equivalente a "sin filtro".

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/filters/` | Lista todos los filtros |
| `GET` | `/filters/{fid}` | Obtiene un filtro específico |
| `POST` | `/filters/` | Crea un filtro nuevo |
| `PATCH` | `/filters/{fid}` | Actualiza el filtro (delete + recrear internamente) |
| `DELETE` | `/filters/{fid}` | Elimina el filtro |

> **Importante:** Jasmin no tiene comando `filter --update` en jcli. El `PATCH` internamente elimina el filtro y lo recrea. Si el filtro está siendo usado por rutas o interceptores activos, esas referencias pueden quedar temporalmente inconsistentes durante la operación.

---

## Parámetros generales

### POST `/filters/` — Crear

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `fid` | `string` | Sí | Identificador único del filtro. Referenciado en rutas e interceptores. Ejemplo: `"filter_mx_src"` |
| `type` | `string` | Sí | Tipo de filtro. Ver tabla de tipos abajo. |
| `params` | `object` | No | Parámetros específicos del tipo. Ver por tipo abajo. Default: `{}` |

### PATCH `/filters/{fid}` — Actualizar

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `type` | `string` | Sí | Nuevo tipo de filtro |
| `params` | `object` | No | Nuevos parámetros |

---

## Tipos de filtro

### `TransparentFilter`

**Coincide siempre.** No tiene parámetros. Úsalo en rutas `DefaultRoute`, `StaticMTRoute`, `StaticMORoute` o interceptores que deben aplicar a todos los mensajes sin distinción.

```json
{
  "fid": "transparent",
  "type": "TransparentFilter",
  "params": {}
}
```

---

### `ConnectorFilter`

Coincide si el mensaje **fue recibido por un conector SMPP específico** (solo aplica a rutas/interceptores MO).

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `cid` | `string` | ID del conector SMPP de origen |

```json
{
  "fid": "from_carrier_a",
  "type": "ConnectorFilter",
  "params": { "cid": "carrier_mx" }
}
```

---

### `UserFilter`

Coincide si el mensaje **fue enviado por un usuario Jasmin específico** (solo aplica a MT).

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `uid` | `string` | UID del usuario Jasmin |

```json
{
  "fid": "only_tenant_acme",
  "type": "UserFilter",
  "params": { "uid": "tenant_acme_01" }
}
```

---

### `GroupFilter`

Coincide si el usuario que envía el mensaje **pertenece a un grupo específico**.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `gid` | `string` | GID del grupo Jasmin |

```json
{
  "fid": "premium_group_filter",
  "type": "GroupFilter",
  "params": { "gid": "premium_tier" }
}
```

**Uso típico:** tener diferentes rutas MT (con diferentes carriers) para usuarios premium vs. estándar.

---

### `SourceAddrFilter`

Coincide si el **número o sender ID de origen** del mensaje cumple la expresión regular.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `source_addr` | `string` | Expresión regular Python |

```json
{
  "fid": "from_mexico",
  "type": "SourceAddrFilter",
  "params": { "source_addr": "^\\+?52" }
}
```

**Ejemplos de regex:**

| Regex | Coincide con |
|-------|-------------|
| `^\\+?52` | Números mexicanos (+521234567890 o 521234567890) |
| `^EMPRESA$` | Exactamente el sender ID "EMPRESA" |
| `^\\+1[2-9]` | Números de EEUU/Canadá |
| `.*` | Cualquier cosa |

---

### `DestinationAddrFilter`

Coincide si el **número destino** del mensaje cumple la expresión regular.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `destination_addr` | `string` | Expresión regular Python |

```json
{
  "fid": "to_mx_only",
  "type": "DestinationAddrFilter",
  "params": { "destination_addr": "^\\+?521" }
}
```

---

### `ShortMessageFilter`

Coincide si el **texto del mensaje** cumple la expresión regular.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `short_message` | `string` | Expresión regular Python |

```json
{
  "fid": "stop_messages",
  "type": "ShortMessageFilter",
  "params": { "short_message": "(?i)^STOP\\s*$" }
}
```

**Uso típico:** rutas MO separadas según el contenido del mensaje (comandos de baja, OTP responses, etc.).

---

### `DateIntervalFilter`

Coincide si la **fecha actual** está dentro del intervalo especificado (inclusive en ambos extremos).

| Parámetro | Tipo | Formato | Descripción |
|-----------|------|---------|-------------|
| `dateInterval` | `string` | `"YYYY-MM-DD;YYYY-MM-DD"` | Fecha inicio y fecha fin separadas por `;` |

```json
{
  "fid": "campaign_q1",
  "type": "DateIntervalFilter",
  "params": { "dateInterval": "2024-01-01;2024-03-31" }
}
```

**Uso típico:** rutas o interceptores activos solo durante una campaña o período promocional.

---

### `TimeIntervalFilter`

Coincide si la **hora actual** está dentro del intervalo especificado (según el timezone del servidor Jasmin).

| Parámetro | Tipo | Formato | Descripción |
|-----------|------|---------|-------------|
| `timeInterval` | `string` | `"HH:MM:SS;HH:MM:SS"` | Hora inicio y hora fin separadas por `;` |

```json
{
  "fid": "business_hours",
  "type": "TimeIntervalFilter",
  "params": { "timeInterval": "09:00:00;18:00:00" }
}
```

**Uso típico:** ruta MT activa solo en horario laboral; fuera de ese horario, los mensajes caen a una ruta alternativa (ej: encolar o rechazar).

---

### `EvalPyFilter`

Coincide si una **expresión Python** evaluada en el contexto del mensaje retorna `True`.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `pyCode` | `string` | Código Python que debe evaluarse a `True` o `False`. El objeto `routable` está disponible. |

```json
{
  "fid": "only_long_messages",
  "type": "EvalPyFilter",
  "params": { "pyCode": "len(routable.pdu.params['short_message']) > 100" }
}
```

**Variables disponibles en `pyCode`:**

| Variable | Descripción |
|----------|-------------|
| `routable` | Objeto del mensaje con todo su contexto |
| `routable.pdu.params['short_message']` | Texto del mensaje |
| `routable.pdu.params['source_addr']` | Número origen |
| `routable.pdu.params['destination_addr']` | Número destino |
| `routable.pdu.params['priority_flag']` | Prioridad |

> **Precaución:** Este filtro ejecuta código Python arbitrario en el proceso de Jasmin. Úsalo solo con código confiable. Un error de sintaxis o excepción en `pyCode` hace que el filtro no coincida (falla silenciosa en algunos casos).

---

### `TagFilter`

Coincide si el mensaje tiene un **tag numérico específico** asignado.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `tag` | `int` | Número entero del tag |

```json
{
  "fid": "tagged_priority",
  "type": "TagFilter",
  "params": { "tag": 99 }
}
```

**Uso típico:** los interceptores pueden asignar tags a mensajes para que rutas posteriores los seleccionen de forma más eficiente que una expresión regular.

---

## Tabla resumen de tipos

| Tipo | Inspecciona | Parámetro requerido | Ejemplo de uso |
|------|-------------|---------------------|----------------|
| `TransparentFilter` | Nada | Ninguno | Rutas catch-all |
| `ConnectorFilter` | Conector de origen | `cid` | Separar por carrier |
| `UserFilter` | Usuario emisor | `uid` | Ruta dedicada a un tenant |
| `GroupFilter` | Grupo del usuario | `gid` | Tier premium vs estándar |
| `SourceAddrFilter` | Número origen | `source_addr` (regex) | Solo números de un país |
| `DestinationAddrFilter` | Número destino | `destination_addr` (regex) | Solo ciertos prefijos |
| `ShortMessageFilter` | Texto del mensaje | `short_message` (regex) | Comandos MO (STOP, INFO) |
| `DateIntervalFilter` | Fecha actual | `dateInterval` | Campañas por período |
| `TimeIntervalFilter` | Hora actual | `timeInterval` | Horario de atención |
| `EvalPyFilter` | Cualquier cosa | `pyCode` | Lógica compleja custom |
| `TagFilter` | Tag del mensaje | `tag` | Routing por tag |

---

## Combinación de filtros

Cuando una ruta o interceptor tiene múltiples filtros, **todos** deben coincidir (operación AND). Si necesitas OR, crea múltiples rutas con distintos filtros al mismo orden no es posible — usa `EvalPyFilter` con una expresión compuesta, o crea rutas separadas.

**Ejemplo — AND implícito:**
```
Ruta MT con filtros: [GroupFilter(gid=premium), TimeIntervalFilter(09:00-18:00)]
→ Aplica solo si el usuario es premium Y el mensaje se envía en horario laboral
```

---

## Ejemplos completos

### Filtro de horario laboral

```bash
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "fid": "horario_laboral",
    "type": "TimeIntervalFilter",
    "params": { "timeInterval": "08:00:00;18:00:00" }
  }'
```

### Filtro para números mexicanos (destino)

```bash
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "fid": "destino_mexico",
    "type": "DestinationAddrFilter",
    "params": { "destination_addr": "^\\+?521?[2-9]\\d{9}$" }
  }'
```

### Filtro para mensajes de baja (MO)

```bash
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "fid": "comando_stop",
    "type": "ShortMessageFilter",
    "params": { "short_message": "(?i)^(stop|baja|cancelar)\\s*$" }
  }'
```

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | Error de Jasmin | Tipo de filtro desconocido, parámetro inválido |
| 404 | `Filter '{fid}' not found` | El filtro no existe |
| 409 | `Filter '{fid}' already exists` | FID duplicado |
| 503 | `Jasmin is not available` | Telnet desconectado |
