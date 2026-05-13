# Interceptores MT (`/mt-interceptors`)

## Qué son

Un interceptor MT es un **script Python que Jasmin ejecuta sobre cada mensaje saliente antes de enrutarlo**. El script recibe el mensaje completo (PDU SMPP) y puede:

- Leer cualquier campo del mensaje (origen, destino, contenido, prioridad)
- **Modificar** campos del PDU (cambiar el sender ID, modificar el texto, ajustar la prioridad)
- **Rechazar** el mensaje (no se envía, el cliente recibe un error)
- Realizar lógica personalizada (billing alternativo, logging, enriquecimiento de datos)

Los interceptores MT son opcionales pero muy poderosos. La mayoría de los deployments simples no los necesitan — las reglas de usuarios (balance, filtros de valor) y las rutas son suficientes para el routing estándar.

---

## Lugar en el flujo

```
POST /sms/send → Jasmin autentica usuario → filtros de valor del usuario
    │
    ▼ MT Interceptors (orden ascendente)
    
    Interceptor order=0: DefaultInterceptor (script: audit_log.py)
        → Script ejecuta: registra el mensaje en un log externo
        → No modifica, no rechaza → el mensaje continúa
    
    Interceptor order=5: StaticMTInterceptor (filtros: [UserFilter(premium)])
        → Solo aplica si el usuario es premium
        → Script ajusta la prioridad del PDU a 3 (máxima)
        → Mensaje continúa con prioridad modificada
    │
    ▼ MT Routes → envío por SMPP Connector
```

Los interceptores se ejecutan **antes** del enrutamiento. Modificaciones al PDU realizadas en el interceptor afectan el mensaje que eventualmente llega al carrier.

---

## Tipos de interceptor

| Tipo | Filtros | Aplica a |
|------|---------|---------|
| `DefaultInterceptor` | Ninguno (no acepta filtros) | Todos los mensajes MT sin excepción |
| `StaticMTInterceptor` | 1 o más (obligatorio) | Solo mensajes cuyos filtros coincidan |

Solo puede existir **un** `DefaultInterceptor` (siempre en order 0). Puede haber múltiples `StaticMTInterceptor` en distintos orders.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/mt-interceptors/` | Lista todos los interceptores MT |
| `GET` | `/mt-interceptors/{order}` | Obtiene un interceptor por su order |
| `POST` | `/mt-interceptors/` | Crea un interceptor nuevo |
| `PATCH` | `/mt-interceptors/{order}` | Actualiza el script o los filtros |
| `DELETE` | `/mt-interceptors/{order}` | Elimina un interceptor |
| `DELETE` | `/mt-interceptors/flush` | Elimina **todos** los interceptores MT |

---

## Parámetros

### POST `/mt-interceptors/` — Crear

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `type` | `string` | Sí | `"DefaultInterceptor"` o `"StaticMTInterceptor"` |
| `order` | `int` | Sí | Posición en la cadena de evaluación. Menor = se ejecuta primero. `DefaultInterceptor` siempre va en order 0. |
| `filters` | `list[string]` | Solo en `StaticMTInterceptor` | Lista de FIDs. Todos deben existir. Ignorado en `DefaultInterceptor`. |
| `script` | `string` | Sí | Código fuente Python completo. Debe ser un módulo válido (no puede tener `return` a nivel de módulo). El objeto `routable` está disponible automáticamente. |

### PATCH `/mt-interceptors/{order}` — Actualizar

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `filters` | `list[string] \| null` | Nueva lista de filtros. `null` = reutiliza los actuales (recuperados del disco). |
| `script` | `string \| null` | Nuevo código Python. `null` = reutiliza el script guardado en disco. Si el archivo fue eliminado manualmente, este campo es obligatorio. |

### Respuesta (`InterceptorOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `order` | `int` | Posición en la cadena |
| `type` | `string` | Tipo de interceptor |
| `filters` | `list[string]` | Siempre `[]` — Jasmin no expone FIDs en la respuesta de show |
| `script_path` | `string` | Ruta absoluta en disco donde se guardó el script |

---

## El script Python

### Cómo funciona

El script se guarda en disco en `JASMIN_SCRIPTS_DIR` (por defecto `/etc/jasmin/scripts/`) con el nombre `mt_{order}.py`. Jasmin lo carga y ejecuta para cada mensaje que coincida con el interceptor.

El objeto `routable` está inyectado en el namespace del script. Contiene el PDU SMPP completo y el contexto del mensaje.

### Variables disponibles

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `routable` | `Routable` | El mensaje completo con todo su contexto |
| `routable.pdu` | `PDU` | PDU SMPP del mensaje |
| `routable.pdu.params` | `dict` | Campos del PDU |
| `routable.pdu.params['source_addr']` | `str` | Número u origen del mensaje |
| `routable.pdu.params['destination_addr']` | `str` | Número destino |
| `routable.pdu.params['short_message']` | `bytes` | Contenido del mensaje |
| `routable.pdu.params['priority_flag']` | `int` | Prioridad (0–3) |
| `routable.pdu.params['data_coding']` | `int` | Codificación (0=GSM7, 8=UCS2) |

### Rechazar un mensaje

Para rechazar el mensaje (no se envía, el cliente recibe error), asignar `REJECT` al `routable`:

```python
# Rechazar mensajes vacíos
if not routable.pdu.params.get('short_message'):
    raise jasmin.routing.Routables.InvalidRoutableError("Empty message rejected")
```

En la práctica, el mecanismo exacto de rechazo varía según la versión de Jasmin. El approach más portátil es dejar que el script termine con una excepción, lo que hace que Jasmin marque el mensaje como no entregable.

### Modificar campos

```python
# Cambiar el sender ID
routable.pdu.params['source_addr'] = 'EMPRESA'

# Modificar el texto
original = routable.pdu.params['short_message'].decode('utf-8', errors='replace')
routable.pdu.params['short_message'] = f"[{original}]".encode('utf-8')

# Aumentar prioridad
routable.pdu.params['priority_flag'] = 3
```

---

## Ejemplos de scripts

### Script mínimo (pass-through)

```python
# Pass-through — el mensaje continúa sin modificaciones
```

Solo un comentario es suficiente. No hace nada; el mensaje pasa.

### Logging de mensajes salientes

```python
import logging
logger = logging.getLogger('jasmin.interceptor')

uid = getattr(routable, 'user', {}).get('uid', 'unknown') if hasattr(routable, 'user') else 'unknown'
dst = routable.pdu.params.get('destination_addr', '')
logger.info(f"MT send: uid={uid} dst={dst}")
```

### Forzar sender ID para un interceptor específico

```python
# Siempre usar "EMPRESA" como sender ID para este grupo de usuarios
routable.pdu.params['source_addr'] = b'EMPRESA'
```

### Validar número destino

```python
import re
dst = routable.pdu.params.get('destination_addr', b'').decode('ascii', errors='replace')
if not re.match(r'^\+?52\d{10}$', dst):
    raise Exception(f"Número destino inválido: {dst}")
```

### Script con lógica condicional

```python
import re
content = routable.pdu.params.get('short_message', b'').decode('utf-8', errors='replace')

# Si el mensaje contiene URLs, agregarle un disclaimer
if re.search(r'https?://', content):
    routable.pdu.params['short_message'] = (content + '\n[Enlace verificado]').encode('utf-8')
```

---

## Ejemplos de endpoints

### Crear un DefaultInterceptor de logging

```bash
SCRIPT=$(cat << 'PYEOF'
import logging
logger = logging.getLogger('jasmin.mt')
dst = routable.pdu.params.get('destination_addr', b'').decode('ascii', errors='replace')
logger.info(f"MT outbound to {dst}")
PYEOF
)

curl -X POST https://api.example.com/api/v1/mt-interceptors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"DefaultInterceptor\",
    \"order\": 0,
    \"script\": $(echo "$SCRIPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')
  }"
```

### Crear un interceptor para usuarios premium

```bash
# Primero crear el filtro
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"fid": "f_premium", "type": "GroupFilter", "params": {"gid": "premium"}}'

# Crear el interceptor que sube la prioridad para premium
curl -X POST https://api.example.com/api/v1/mt-interceptors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "StaticMTInterceptor",
    "order": 5,
    "filters": ["f_premium"],
    "script": "routable.pdu.params[\"priority_flag\"] = 3\n"
  }'
```

### Actualizar el script

```bash
curl -X PATCH https://api.example.com/api/v1/mt-interceptors/5 \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": ["f_premium"],
    "script": "# Script actualizado\nroutable.pdu.params[\"priority_flag\"] = 2\n"
  }'
```

---

## Consideraciones de producción

### Validación de sintaxis

La API valida la sintaxis Python del script **antes** de enviarlo a Jasmin (usando `compile()`). Si el script tiene un error de sintaxis, la API retorna 422 con el error antes de que llegue a Jasmin.

```json
{
  "detail": [
    {
      "loc": ["body", "script"],
      "msg": "Value error, Script is not valid Python: invalid syntax (<interceptor_script>, line 1)",
      "type": "value_error"
    }
  ]
}
```

### El script no puede tener `return` a nivel de módulo

```python
# ❌ Inválido — SyntaxError
return routable

# ✅ Válido — lógica a nivel de módulo
routable.pdu.params['source_addr'] = b'EMPRESA'
```

### Los errores en el script en runtime

Si el script lanza una excepción durante la ejecución (no de sintaxis), Jasmin puede rechazar el mensaje o ignorar el error según la versión. Siempre testear los scripts en un entorno de staging antes de producción.

### Los scripts persisten en disco

Los scripts se guardan en `/etc/jasmin/scripts/mt_{order}.py`. Si se elimina el interceptor via API, el archivo en disco **no** se elimina automáticamente (limpieza manual si es necesario). Si se actualiza un interceptor, el archivo sí se sobreescribe.

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | Error de Jasmin | Script inválido en runtime, campos faltantes |
| 400 | `Script file not found on disk...` | PATCH sin `script` y el archivo fue eliminado manualmente |
| 404 | `MT interceptor with order {order} not found` | El interceptor no existe |
| 409 | `MT interceptor with order {order} already exists` | Order duplicado |
| 422 | `Script is not valid Python: ...` | Error de sintaxis Python en el script |
| 503 | `Jasmin is not available` | Telnet desconectado |
