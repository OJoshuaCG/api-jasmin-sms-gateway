# Uso de la API — Jasmin API Gateway

## Base URL y autenticación

Todos los endpoints están bajo `/api/v1/`. Todas las solicitudes **requieren** el header `X-API-Key`:

```
https://api.tudominio.com/api/v1/<recurso>
```

```bash
# Header requerido en cada solicitud
X-API-Key: <tu-admin-api-key>
```

El único endpoint público es:
```bash
GET /health   # sin autenticación
```

---

## Formato de respuesta

Todas las respuestas exitosas siguen el mismo formato:

```json
{
  "success": true,
  "data": { ... },
  "message": "Mensaje opcional",
  "meta": { ... }    // Solo en listas paginadas
}
```

Los errores siguen:

```json
{
  "success": false,
  "message": "Descripción del error",
  "status_code": 404
}
```

---

## Solicitudes desde fuera del servidor

### curl (bash / terminal)

```bash
BASE="https://api.tudominio.com/api/v1"
KEY="tu-api-key-aqui"

# Listar grupos
curl -s -H "X-API-Key: $KEY" "$BASE/groups/"

# Crear usuario
curl -s -X POST "$BASE/users/" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "cliente1",
    "gid": "grupo_a",
    "password": "pass123",
    "balance": 100.0,
    "sms_count": 500
  }'

# Enviar SMS
curl -s -X POST "$BASE/sms/send" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "cliente1",
    "password": "pass123",
    "to": "50212345678",
    "content": "Hola mundo",
    "dlr_params": { "org_id": 12 }
  }'
```

> El DLR está centralizado en el gateway: la URL destino se define en las
> variables de entorno (`DLR_URL`) y **no** se envía en el body. Con
> `DLR_ENABLED=true` todos los envíos solicitan DLR y los `dlr_params` se
> concatenan como query params a esa URL. Los campos `dlr_url`/`dlr_method`/`dlr_level`
> del body solo aplican en modo legacy (`DLR_ENABLED=false`).

### Python (httpx)

```python
import httpx

client = httpx.Client(
    base_url="https://api.tudominio.com/api/v1",
    headers={"X-API-Key": "tu-api-key-aqui"},
    timeout=30.0,
)

# Listar conectores SMPP
response = client.get("/smpp-connectors/")
connectors = response.json()["data"]

# Crear conector SMPP
response = client.post("/smpp-connectors/", json={
    "cid": "proveedor1",
    "host": "smpp.proveedor.com",
    "port": 2775,
    "username": "mi_usuario",
    "password": "mipass",
    "bind_to": "transceiver",
    "submit_throughput": 10.0,
})
connector = response.json()["data"]

# Iniciar conector
response = client.post(f"/smpp-connectors/{connector['cid']}/start")
```

### PHP

```php
<?php
$base = 'https://api.tudominio.com/api/v1';
$apiKey = 'tu-api-key-aqui';

$ch = curl_init("$base/groups/");
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        "X-API-Key: $apiKey",
        "Content-Type: application/json",
    ],
]);
$response = json_decode(curl_exec($ch), true);
curl_close($ch);

foreach ($response['data'] as $group) {
    echo $group['gid'] . "\n";
}
```

### JavaScript / Node.js (fetch)

```javascript
const BASE = 'https://api.tudominio.com/api/v1';
const KEY = 'tu-api-key-aqui';

const headers = {
  'X-API-Key': KEY,
  'Content-Type': 'application/json',
};

// Listar usuarios
const res = await fetch(`${BASE}/users/`, { headers });
const { data: users } = await res.json();

// Crear ruta MT
await fetch(`${BASE}/mt-routes/`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    type: 'DefaultRoute',
    order: 0,
    connectors: ['proveedor1'],
  }),
});
```

---

## Solicitudes desde dentro del servidor (acceso local)

Si haces solicitudes desde el mismo servidor donde corre el gateway, usa `localhost` directamente sin pasar por Nginx:

```bash
BASE="http://localhost:8000/api/v1"
KEY="tu-api-key-aqui"

curl -s -H "X-API-Key: $KEY" "$BASE/groups/"
```

Esto es útil para scripts de mantenimiento, cronjobs o aplicaciones en el mismo host.

---

## Referencia de endpoints

### Sistema

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Estado del servidor (sin autenticación) |
| `POST` | `/system/persist` | Persistir configuración Jasmin a disco |
| `POST` | `/system/reload` | Recargar configuración desde disco |
| `POST` | `/system/reconnect` | Reconectar sesión Telnet con Jasmin |
| `GET` | `/system/session` | Estado de la sesión Telnet |

### Grupos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/groups/` | Listar grupos |
| `GET` | `/groups/{gid}` | Obtener grupo |
| `POST` | `/groups/` | Crear grupo |
| `PATCH` | `/groups/{gid}` | Habilitar/deshabilitar grupo |
| `DELETE` | `/groups/{gid}` | Eliminar grupo |

### Usuarios

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/users/` | Listar usuarios (datos completos) |
| `GET` | `/users/{uid}` | Obtener usuario |
| `POST` | `/users/` | Crear usuario |
| `PATCH` | `/users/{uid}` | Actualizar usuario |
| `DELETE` | `/users/{uid}` | Eliminar usuario |
| `PATCH` | `/users/{uid}/status` | Habilitar/deshabilitar usuario |

### Conectores SMPP

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/smpp-connectors/` | Listar conectores |
| `GET` | `/smpp-connectors/{cid}` | Obtener conector |
| `POST` | `/smpp-connectors/` | Crear conector |
| `PATCH` | `/smpp-connectors/{cid}` | Actualizar conector |
| `DELETE` | `/smpp-connectors/{cid}` | Eliminar conector |
| `POST` | `/smpp-connectors/{cid}/start` | Iniciar conector |
| `POST` | `/smpp-connectors/{cid}/stop` | Detener conector |
| `GET` | `/smpp-connectors/{cid}/status` | Estado del conector |

### Conectores HTTP

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/http-connectors/` | Listar conectores HTTP |
| `GET` | `/http-connectors/{cid}` | Obtener conector HTTP |
| `POST` | `/http-connectors/` | Crear conector HTTP |
| `PATCH` | `/http-connectors/{cid}` | Actualizar conector HTTP |
| `DELETE` | `/http-connectors/{cid}` | Eliminar conector HTTP |

### Filtros

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/filters/` | Listar filtros |
| `GET` | `/filters/{fid}` | Obtener filtro |
| `POST` | `/filters/` | Crear filtro |
| `PATCH` | `/filters/{fid}` | Actualizar filtro |
| `DELETE` | `/filters/{fid}` | Eliminar filtro |

**Tipos de filtro disponibles:** `TransparentFilter`, `ConnectorFilter`, `UserFilter`, `GroupFilter`, `SrcAddrFilter`, `DstAddrFilter`, `ShortMessageFilter`, `DateIntervalFilter`, `TimeIntervalFilter`, `DayFilter`, `EvalPyFilter`, `TagFilter`

### Rutas MT (Mobile Terminated)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/mt-routes/` | Listar rutas MT |
| `GET` | `/mt-routes/{order}` | Obtener ruta MT |
| `POST` | `/mt-routes/` | Crear ruta MT |
| `PATCH` | `/mt-routes/{order}` | Actualizar ruta MT |
| `DELETE` | `/mt-routes/{order}` | Eliminar ruta MT |
| `DELETE` | `/mt-routes/flush` | Eliminar todas las rutas MT |

### Rutas MO (Mobile Originated)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/mo-routes/` | Listar rutas MO |
| `GET` | `/mo-routes/{order}` | Obtener ruta MO |
| `POST` | `/mo-routes/` | Crear ruta MO |
| `PATCH` | `/mo-routes/{order}` | Actualizar ruta MO |
| `DELETE` | `/mo-routes/{order}` | Eliminar ruta MO |
| `DELETE` | `/mo-routes/flush` | Eliminar todas las rutas MO |

### Interceptores MT / MO

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/mt-interceptors/` | Listar interceptores MT |
| `POST` | `/mt-interceptors/` | Crear interceptor MT |
| `PATCH` | `/mt-interceptors/{order}` | Actualizar interceptor MT |
| `DELETE` | `/mt-interceptors/{order}` | Eliminar interceptor MT |
| `DELETE` | `/mt-interceptors/flush` | Eliminar todos los interceptores MT |
| `GET` | `/mo-interceptors/` | Listar interceptores MO |
| `POST` | `/mo-interceptors/` | Crear interceptor MO |
| `PATCH` | `/mo-interceptors/{order}` | Actualizar interceptor MO |
| `DELETE` | `/mo-interceptors/{order}` | Eliminar interceptor MO |
| `DELETE` | `/mo-interceptors/flush` | Eliminar todos los interceptores MO |

### Servidor SMPP

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/smpp-server/` | Configuración del servidor SMPP |
| `PATCH` | `/smpp-server/` | Actualizar configuración |

### Estadísticas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/stats/` | Estadísticas globales |
| `GET` | `/stats/smpp-connectors/{cid}` | Stats por conector SMPP |
| `GET` | `/stats/users/{uid}` | Stats por usuario |

### SMS (HTTP API de Jasmin)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/sms/send` | Enviar SMS de texto |
| `POST` | `/sms/send/binary` | Enviar SMS binario |
| `GET` | `/sms/rate` | Consultar tarifa de envío |
| `GET` | `/sms/balance` | Consultar balance de usuario |

---

## Ejemplos completos

### Configurar un conector SMPP y una ruta por defecto

```bash
BASE="https://api.tudominio.com/api/v1"
KEY="tu-api-key"

# 1. Crear conector SMPP
curl -s -X POST "$BASE/smpp-connectors/" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "cid": "proveedor_a",
    "host": "smpp.proveedor.com",
    "port": 2775,
    "username": "mi_user",
    "password": "mi_pass",
    "bind_to": "transceiver",
    "submit_throughput": 20.0
  }'

# 2. Iniciar el conector
curl -s -X POST "$BASE/smpp-connectors/proveedor_a/start" \
  -H "X-API-Key: $KEY"

# 3. Crear grupo de usuarios
curl -s -X POST "$BASE/groups/" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"gid": "clientes"}'

# 4. Crear usuario SMS
curl -s -X POST "$BASE/users/" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "cliente1",
    "gid": "clientes",
    "password": "pass123",
    "balance": 500.0,
    "sms_count": 1000,
    "mt_throughput": 5.0
  }'

# 5. Crear ruta MT por defecto
curl -s -X POST "$BASE/mt-routes/" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "DefaultRoute",
    "order": 0,
    "connectors": ["proveedor_a"]
  }'

# 6. Enviar SMS de prueba
curl -s -X POST "$BASE/sms/send" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "cliente1",
    "password": "pass123",
    "to": "50212345678",
    "content": "Mensaje de prueba"
  }'
```

### Consultar balance de un usuario

```bash
# Vía admin (muestra balance almacenado en Jasmin)
curl -H "X-API-Key: $KEY" "$BASE/users/cliente1"

# Vía HTTP API de Jasmin (balance en tiempo real)
curl "$BASE/sms/balance?username=cliente1&password=pass123" \
  -H "X-API-Key: $KEY"
```

---

## Documentación interactiva (Swagger)

Si `DOCS_ENABLED=True`, la documentación interactiva está disponible en:

- **Swagger UI:** `https://api.tudominio.com/api/v1/docs`
- **ReDoc:** `https://api.tudominio.com/api/v1/redoc`

Desde Swagger puedes probar cualquier endpoint directamente en el navegador. Para autenticarte, haz clic en el botón **Authorize** e ingresa tu API Key.
