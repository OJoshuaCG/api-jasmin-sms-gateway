# Rutas MO (`/mo-routes`)

## Qué son

Una ruta MO (Mobile Originated) define **a qué destino se entrega un mensaje entrante** recibido desde el carrier. Cuando Jasmin recibe un SMS de un usuario final (vía el SMPP bind del carrier), evalúa las rutas MO en orden ascendente y entrega el mensaje al conector HTTP de la primera ruta cuyos filtros coincidan.

Las rutas MO son el complemento entrante de las rutas MT. Mientras las rutas MT definen por dónde salen los mensajes, las rutas MO definen a dónde llegan los mensajes que se reciben.

---

## Lugar en el flujo

```
Usuario final envía SMS al número del carrier
    → Carrier entrega el MO al SMPP bind de Jasmin
    → Jasmin ejecuta MO Interceptors (orden ascendente)
    → Jasmin evalúa rutas MO (orden ascendente)
         Ruta order=5:  filtros [ShortMessageFilter(^STOP)] → ¿coincide? No
         Ruta order=10: filtros [ConnectorFilter(cid=mx)]   → ¿coincide? Sí
         → Entregar a conector http(webhook_crm)
    → Jasmin hace POST/GET a la URL del HTTP Connector
```

---

## Tipos de ruta MO

| Tipo | Conector | Filtros | Comportamiento |
|------|---------|---------|----------------|
| `DefaultRoute` | 1 HTTP Connector | Ninguno | Catch-all. Siempre almacenada en order 0 por Jasmin. |
| `StaticMORoute` | 1 HTTP Connector | 1 o más | Entrega al conector cuando los filtros coinciden. |

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/mo-routes/` | Lista todas las rutas MO |
| `GET` | `/mo-routes/{order}` | Obtiene una ruta por su order |
| `POST` | `/mo-routes/` | Crea una ruta nueva |
| `PATCH` | `/mo-routes/{order}` | Actualiza una ruta |
| `DELETE` | `/mo-routes/{order}` | Elimina una ruta |
| `DELETE` | `/mo-routes/flush` | Elimina **todas** las rutas MO |

---

## Parámetros

### POST `/mo-routes/` — Crear

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `type` | `string` | Sí | `"DefaultRoute"` o `"StaticMORoute"` |
| `order` | `int` | Sí | Prioridad de evaluación. Menor = mayor prioridad. `DefaultRoute` siempre queda en order 0. |
| `connector` | `string` | Sí | ID del HTTP Connector con prefijo. Formato: `"http(<cid>)"`. |
| `filters` | `list[string]` | No | Lista de FIDs de filtros. Vacío `[]` para `DefaultRoute`. Para `StaticMORoute`, si se omite o está vacío, se auto-resuelve con el primer `TransparentFilter` disponible. |

### PATCH `/mo-routes/{order}` — Actualizar

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connector` | `string \| null` | Nuevo conector HTTP. `null` = mantener el actual. |
| `filters` | `list[string] \| null` | Nueva lista de filtros. `null` = auto-detectar si es TransparentFilter; si usa filtros reales, obligatorio. |

### Respuesta (`MoRouteOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `order` | `int` | Posición en la cadena de evaluación |
| `type` | `string` | Tipo de ruta |
| `connector` | `string` | Conector HTTP asignado (con prefijo `http(...)`) |
| `filters` | `list[string]` | Siempre `[]` — Jasmin no expone FIDs en la respuesta de `route -s` |

---

## Sintaxis del conector

Los conectores HTTP se referencian con el prefijo `http()`:

```
"http(webhook_crm)"
"http(test_listener)"
```

El valor dentro de los paréntesis es el `cid` del HTTP Connector creado previamente.

---

## Ejemplos

### Configuración mínima: entregar todos los MO a un webhook

```bash
# 1. Crear el HTTP Connector
curl -X POST https://api.example.com/api/v1/http-connectors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cid": "webhook_principal",
    "url": "https://myapp.com/sms/inbound",
    "method": "POST"
  }'

# 2. Crear la DefaultRoute
curl -X POST https://api.example.com/api/v1/mo-routes/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "DefaultRoute",
    "order": 0,
    "connector": "http(webhook_principal)"
  }'
```

Con esto, todos los MO recibidos se entregan a `webhook_principal`.

---

### Routing por contenido (comandos de baja vs mensajes normales)

```bash
# Filtro para detectar mensajes de baja
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"fid": "f_stop", "type": "ShortMessageFilter", "params": {"short_message": "(?i)^stop\\s*$"}}'

# Ruta para mensajes STOP → endpoint de bajas (order=5, alta prioridad)
curl -X POST https://api.example.com/api/v1/mo-routes/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{
    "type": "StaticMORoute",
    "order": 5,
    "connector": "http(unsubscribe_handler)",
    "filters": ["f_stop"]
  }'

# Fallback para todos los demás MO (DefaultRoute)
curl -X POST https://api.example.com/api/v1/mo-routes/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{
    "type": "DefaultRoute",
    "order": 0,
    "connector": "http(general_inbox)"
  }'
```

---

### Routing por número de origen (por carrier)

```bash
# Filtro para mensajes del carrier A (solo ciertos prefijos)
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"fid": "f_carrier_a", "type": "ConnectorFilter", "params": {"cid": "carrier_a"}}'

# MO del carrier A → sistema A
curl -X POST https://api.example.com/api/v1/mo-routes/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{
    "type": "StaticMORoute",
    "order": 10,
    "connector": "http(sistema_a)",
    "filters": ["f_carrier_a"]
  }'

# MO de cualquier otro carrier → sistema general
curl -X POST https://api.example.com/api/v1/mo-routes/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"type": "DefaultRoute", "order": 0, "connector": "http(sistema_general)"}'
```

---

### Actualizar el webhook de una ruta

```bash
curl -X PATCH https://api.example.com/api/v1/mo-routes/5 \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "connector": "http(nuevo_webhook)",
    "filters": ["f_stop"]
  }'
```

---

## Diferencias clave con rutas MT

| Aspecto | MT Routes | MO Routes |
|---------|-----------|-----------|
| Dirección | Saliente (Jasmin → carrier) | Entrante (carrier → Jasmin) |
| Conector destino | SMPP Connector (`smppc(...)`) | HTTP Connector (`http(...)`) |
| Tipos disponibles | Default, Static, RandomRoundrobin, LeastCost | Default, Static |
| Tiene `rate` | Sí | No |

---

## Limitaciones conocidas

### `filters: []` en respuestas de GET

Igual que en rutas MT, Jasmin no expone los FIDs de filtros en `morouter -s`. La respuesta siempre muestra `filters: []`.

### DefaultRoute en order 0

`DefaultRoute` siempre queda almacenada en order 0 por Jasmin. No puede haber más de una `DefaultRoute` en las rutas MO.

### Si no hay ruta MO configurada

Los mensajes MO recibidos no son entregados a ningún destino. Jasmin los procesa pero los descarta sin error visible. Es importante configurar al menos una `DefaultRoute` MO si se espera recibir mensajes.

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | `StaticMORoute requires at least one filter...` | Tipo que requiere filtros pero no hay TransparentFilter disponible |
| 400 | `Cannot update this route without providing 'filters'` | Ruta usa filtros no-transparentes, hay que proveerlos en el PATCH |
| 404 | `MO route with order {order} not found` | La ruta no existe |
| 409 | `MO route with order {order} already exists` | Order duplicado |
| 503 | `Jasmin is not available` | Telnet desconectado |
