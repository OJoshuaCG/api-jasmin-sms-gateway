# Detección de duplicados en endpoints de creación

## Contexto del problema

Todos los endpoints `POST` de creación tenían el mismo bug: si Jasmin rechazaba la creación por duplicado, el error volvía como **400** con el mensaje genérico `"Failed adding connector, check log for details"` porque el código intentaba detectar duplicados leyendo la palabra `"already"` en el output de jcli — palabra que Jasmin no siempre incluye.

---

## Cambio 1 — Lógica de detección de duplicados

**Archivos afectados:**

| Controlador | Método | ID único |
|---|---|---|
| `smpp_connectors_controller.py` | `create_connector` | `cid` |
| `http_connectors_controller.py` | `create_connector` | `cid` |
| `groups_controller.py` | `create_group` | `gid` |
| `users_controller.py` | `create_user` | `uid` |
| `filters_controller.py` | `create_filter` | `fid` |
| `mt_routes_controller.py` | `create_route` | `order` (DefaultRoute → siempre 0) |
| `mo_routes_controller.py` | `create_route` | `order` (DefaultRoute → siempre 0) |
| `interceptors_controller.py` | `create_interceptor` (MT y MO) | `order` |

**Flujo anterior (reactivo — roto):**

```
POST /smpp-connectors/  { cid: "inbtel", ... }
  → jcli: smppccm --add
  → Jasmin rechaza silenciosamente
  → parse del error: ¿contiene "already"? → NO
  → raise 400 "Failed adding connector, check log for details"
```

**Flujo nuevo (proactivo — correcto):**

```
POST /smpp-connectors/  { cid: "inbtel", ... }
  → GET interno: ¿existe "inbtel"?
      ├── Sí (no lanza excepción) → raise 409 "Connector 'inbtel' already exists"
      └── No (lanza 404)         → continuar con smppccm --add
  → jcli: smppccm --add
  → Jasmin crea el conector
  → GET para retornar datos completos → 201
```

**Patrón de código aplicado en todos los controladores:**

```python
try:
    existing = await self.get_connector(data.cid)
    raise AppHttpException(
        f"Connector '{data.cid}' already exists", 409,
        {"cid": data.cid, "existing": existing.model_dump(exclude_none=True)},
    )
except AppHttpException as exc:
    if exc.status_code != 404:
        raise
# Si llegamos aquí → 404 confirmado → proceder con la creación
```

> **Nota para rutas MT/MO:** el `order` a verificar es siempre `0` cuando el tipo es `DefaultRoute`, ya que Jasmin ignora el order enviado y lo fuerza a 0.

---

## Cambio 2 — Respuesta 409 enriquecida con el recurso existente

**Archivos afectados:**
- `app/exceptions/HandlerExceptions.py` — handler central
- Todos los controladores listados arriba

Cuando se detecta un duplicado, la respuesta 409 ahora incluye el campo `existing` con los datos completos del recurso conflictante. Esto elimina la necesidad de que el cliente haga un `GET` adicional para identificar el recurso existente.

**Antes:**

```json
HTTP 409
{
  "detail": {
    "msg": "Connector 'inbtel' already exists",
    "type": "AppHttpException"
  }
}
```

**Ahora:**

```json
HTTP 409
{
  "detail": {
    "msg": "Connector 'inbtel' already exists",
    "type": "AppHttpException",
    "existing": {
      "cid": "inbtel",
      "host": "admin.portaldemensajes.com.mx",
      "port": 2775,
      "username": "Cero208SMPP",
      "bind_to": "transceiver",
      "source_addr_ton": 1,
      "source_addr_npi": 1,
      "dest_addr_ton": 1,
      "dest_addr_npi": 1,
      "submit_throughput": 50.0,
      ...
    }
  }
}
```

El campo `existing` aparece en **todos los entornos** (producción y desarrollo). Solo se incluye en respuestas 409 de duplicado — no afecta ningún otro tipo de error.

El cambio en el handler es mínimo:

```python
# app/exceptions/HandlerExceptions.py
if isinstance(getattr(exc, "context", None), dict) and "existing" in exc.context:
    detail_error["existing"] = exc.context["existing"]
```

---

## Comportamiento por endpoint

Aplica a todos los `POST` de creación:

```
POST /api/v1/smpp-connectors/
POST /api/v1/http-connectors/
POST /api/v1/groups/
POST /api/v1/users/
POST /api/v1/filters/
POST /api/v1/mt-routes/
POST /api/v1/mo-routes/
POST /api/v1/mt-interceptors/
POST /api/v1/mo-interceptors/
```

| Escenario | HTTP | Cuerpo de respuesta |
|---|---|---|
| Recurso no existe → creado | `201` | `{ data: {...}, message: "... created" }` |
| Recurso ya existe | `409` | `{ detail: { msg, type, existing: {...} } }` |
| Jasmin no disponible | `503` | `{ detail: { msg, type } }` |
| Error de validación (campos faltantes/inválidos) | `422` | `{ detail: { msg, type } }` |
| Otro error de jcli | `400` | `{ detail: { msg, type } }` |

---

## Sin cambios en

- Endpoints `GET`, `PATCH`, `DELETE` — comportamiento idéntico
- `update_*` y `delete_*` — ya verificaban existencia antes (patrón original correcto)
- Autenticación, rate limiting, middleware de logging
- Formato de respuestas exitosas (`ApiResponse[T]`)
