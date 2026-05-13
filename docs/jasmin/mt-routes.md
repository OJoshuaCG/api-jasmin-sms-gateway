# Rutas MT (`/mt-routes`)

## Qué son

Una ruta MT (Mobile Terminated) define **por qué conector SMPP se envían los mensajes salientes**. Cuando Jasmin recibe una solicitud de envío, recorre las rutas MT en orden ascendente y usa la primera cuyo(s) filtro(s) coincidan con el mensaje.

Sin al menos una ruta MT configurada, Jasmin no puede entregar ningún mensaje.

---

## Lugar en el flujo

```
POST /sms/send → Jasmin autentica usuario
    → Jasmin ejecuta MT Interceptors (modifican o rechazan)
    → Jasmin evalúa rutas MT (orden ascendente por `order`)
         Ruta order=5:  filtros [UserFilter(uid=premium)]  → ¿coincide? No
         Ruta order=10: filtros [GroupFilter(gid=default)] → ¿coincide? Sí
         → Usar conector smppc(carrier_b)
    → Jasmin envía el mensaje por ese SMPP connector
```

La evaluación es de **menor a mayor `order`**. La primera ruta que coincide gana. Si ninguna coincide, el mensaje es rechazado. La `DefaultRoute` (sin filtros) actúa como fallback.

---

## Tipos de ruta MT

| Tipo | Conectores | Filtros | Rate | Comportamiento |
|------|-----------|---------|------|----------------|
| `DefaultRoute` | 1 | Ninguno | Opcional | Catch-all. Siempre se guarda en order 0 por Jasmin, independiente del valor enviado. |
| `StaticMTRoute` | 1 | 1 o más | Opcional | Envía por un conector fijo cuando los filtros coinciden. |
| `RandomRoundrobinMTRoute` | 2 o más | 1 o más | Opcional | Distribuye mensajes al azar entre los conectores listados. |
| `LeastCostMTRoute` | 2 o más | 1 o más | Opcional | Reservado — no documentado en versiones actuales de Jasmin. |

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/mt-routes/` | Lista todas las rutas |
| `GET` | `/mt-routes/{order}` | Obtiene una ruta por su order |
| `POST` | `/mt-routes/` | Crea una ruta nueva |
| `PATCH` | `/mt-routes/{order}` | Actualiza una ruta (delete + recrear internamente) |
| `DELETE` | `/mt-routes/{order}` | Elimina una ruta |
| `DELETE` | `/mt-routes/flush` | Elimina **todas** las rutas MT |

---

## Parámetros

### POST `/mt-routes/` — Crear

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `type` | `string` | Sí | Tipo de ruta. Ver tabla de tipos. |
| `order` | `int` | Sí | Prioridad de evaluación. Menor = mayor prioridad. Mínimo: 0. `DefaultRoute` siempre queda en 0. |
| `connectors` | `list[string]` | Sí | Lista de IDs de conectores con prefijo. Al menos 1. Formato: `"smppc(<cid>)"`. |
| `filters` | `list[string]` | No | Lista de FIDs de filtros. Vacío `[]` para `DefaultRoute`. Para rutas con tipo que requiere filtros, si se envía vacío se resuelve automáticamente con el primer `TransparentFilter` disponible. |
| `rate` | `float \| null` | No | Costo por mensaje. Se descuenta del `balance` del usuario. `null` o `0.0` = gratis. |

### PATCH `/mt-routes/{order}` — Actualizar

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connectors` | `list[string] \| null` | Nueva lista de conectores. `null` = mantener los actuales. |
| `filters` | `list[string] \| null` | Nueva lista de filtros. `null` = se auto-detecta si la ruta usa TransparentFilter; si usa otros filtros, este campo es obligatorio. |
| `rate` | `float \| null` | Nuevo rate. |

> **Nota sobre PATCH y filtros:** Jasmin no expone los FIDs de filtros en el comando `route -s`. La respuesta de GET siempre muestra `filters: []`. Cuando actualizas sin especificar `filters`, el sidecar detecta si la ruta actual usa un `TransparentFilter` (lo auto-resuelve) o filtros reales (en ese caso debes proveer los FIDs explícitamente).

---

## Sintaxis de conectores

Los conectores se referencian con el prefijo de su tipo:

| Tipo de conector | Sintaxis |
|-----------------|----------|
| SMPP outbound | `smppc(<cid>)` |
| SMPP server (inbound) | `smpps(<cid>)` |

Ejemplo: si tu SMPP connector tiene `cid = "carrier_mx"`, en la ruta usas `"smppc(carrier_mx)"`.

---

## Ejemplos

### Configuración mínima de producción (DefaultRoute)

La configuración mínima para que los mensajes puedan salir:

```bash
# 1. Crear el conector SMPP
curl -X POST https://api.example.com/api/v1/smpp-connectors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cid": "carrier_principal",
    "host": "smpp.carrier.com",
    "port": 2775,
    "username": "myuser",
    "password": "mypass"
  }'

# 2. Iniciarlo
curl -X POST https://api.example.com/api/v1/smpp-connectors/carrier_principal/start \
  -H "X-API-Key: tu-api-key"

# 3. Crear la DefaultRoute
curl -X POST https://api.example.com/api/v1/mt-routes/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "DefaultRoute",
    "order": 0,
    "connectors": ["smppc(carrier_principal)"],
    "rate": 0.0
  }'
```

Con esto, **todos los mensajes MT** irán por `carrier_principal`.

---

### Routing diferenciado por grupo (premium vs estándar)

```bash
# Filtro para usuarios premium
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"fid": "f_premium", "type": "GroupFilter", "params": {"gid": "premium"}}'

# Ruta premium → carrier de alta calidad (order=5, evaluada primero)
curl -X POST https://api.example.com/api/v1/mt-routes/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "StaticMTRoute",
    "order": 5,
    "connectors": ["smppc(carrier_premium)"],
    "filters": ["f_premium"],
    "rate": 0.05
  }'

# Ruta estándar → carrier económico (order=100, fallback para no-premium)
curl -X POST https://api.example.com/api/v1/mt-routes/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "DefaultRoute",
    "order": 0,
    "connectors": ["smppc(carrier_economico)"],
    "rate": 0.02
  }'
```

---

### Round-robin entre dos carriers (load balancing)

```bash
curl -X POST https://api.example.com/api/v1/mt-routes/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "RandomRoundrobinMTRoute",
    "order": 10,
    "connectors": ["smppc(carrier_a)", "smppc(carrier_b)"],
    "filters": ["f_transparent"],
    "rate": 0.03
  }'
```

---

### Ruta por horario (horario laboral vs fuera de horario)

```bash
# Filtro de horario laboral
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"fid": "f_laboral", "type": "TimeIntervalFilter", "params": {"timeInterval": "09:00:00;18:00:00"}}'

# Durante horario laboral → carrier rápido (order=10)
curl -X POST https://api.example.com/api/v1/mt-routes/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"type": "StaticMTRoute", "order": 10, "connectors": ["smppc(carrier_fast)"], "filters": ["f_laboral"]}'

# Fuera de horario → carrier económico (DefaultRoute, order=0)
curl -X POST https://api.example.com/api/v1/mt-routes/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"type": "DefaultRoute", "order": 0, "connectors": ["smppc(carrier_cheap)"]}'
```

---

### Actualizar el conector de una ruta

```bash
curl -X PATCH https://api.example.com/api/v1/mt-routes/10 \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "connectors": ["smppc(carrier_nuevo)"],
    "filters": ["f_premium"]
  }'
```

### Limpiar todas las rutas (útil en migrations o reconfiguración total)

```bash
curl -X DELETE https://api.example.com/api/v1/mt-routes/flush \
  -H "X-API-Key: tu-api-key"
```

---

## Comportamiento del campo `rate`

El `rate` es el costo que Jasmin descuenta del `balance` del usuario por cada mensaje enviado por esta ruta. Si el usuario tiene `balance = 10.0` y la ruta tiene `rate = 0.5`, puede enviar 20 mensajes antes de que su balance llegue a 0.

- `rate = 0.0` o `null` → el mensaje no descuenta balance (gratis)
- Si el `balance` del usuario llega a 0, Jasmin rechaza los envíos aunque haya crédito en el sistema UCaaS

---

## Limitaciones conocidas

### `filters: []` en respuestas de GET

Jasmin no expone los FIDs de filtros en el output de `route -s`. La API siempre retorna `filters: []` en las respuestas de GET, aunque la ruta tenga filtros configurados. Esto es una limitación de Jasmin, no un bug de la API.

### DefaultRoute siempre en order 0

Independientemente del valor de `order` que envíes al crear una `DefaultRoute`, Jasmin siempre la almacena en order 0. Si ya tienes una `DefaultRoute` en order 0, crear otra la sobrescribe (misma posición, no duplicado).

### No hay update nativo

Jasmin no tiene `mtrouter --update`. El `PATCH` internamente hace `delete + add`. Si el delete falla, la ruta se pierde hasta que se recree.

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | `StaticMTRoute requires at least one filter...` | Tipo que requiere filtros pero no hay TransparentFilter disponible |
| 400 | `Cannot update this route without providing 'filters'` | La ruta usa filtros no-transparentes y no se proveyeron en el PATCH |
| 404 | `MT route with order {order} not found` | La ruta no existe |
| 409 | `MT route with order {order} already exists` | Order duplicado |
| 503 | `Jasmin is not available` | Telnet desconectado |
