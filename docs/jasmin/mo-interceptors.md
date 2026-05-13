# Interceptores MO (`/mo-interceptors`)

## Qué son

Un interceptor MO es un **script Python que Jasmin ejecuta sobre cada mensaje entrante antes de entregarlo** al conector HTTP de destino. Funcionan igual que los interceptores MT pero en la dirección opuesta: actúan sobre los mensajes que recibe Jasmin desde el carrier (mensajes que los usuarios finales envían al sistema).

Con un interceptor MO puedes:
- Filtrar mensajes antes de que lleguen al webhook
- Modificar el contenido, origen o destino del MO
- Rechazar mensajes (spam, contenido no deseado)
- Agregar metadata, normalizar números, traducir codificaciones

---

## Lugar en el flujo

```
Usuario final envía SMS al número del carrier
    → Carrier entrega MO al SMPP bind de Jasmin
    │
    ▼ MO Interceptors (orden ascendente)
    
    Interceptor order=0: DefaultInterceptor (normalizar_numero.py)
        → Normaliza el número origen a formato E.164
        → Mensaje continúa con `source_addr` modificado
    
    Interceptor order=5: StaticMOInterceptor (filtros: [ShortMessageFilter(spam)])
        → Solo aplica si el contenido coincide con patrón spam
        → Script rechaza el mensaje
    │
    ▼ MO Routes → entrega al HTTP Connector
```

---

## Tipos de interceptor

| Tipo | Filtros | Aplica a |
|------|---------|---------|
| `DefaultInterceptor` | Ninguno | Todos los mensajes MO sin excepción |
| `StaticMOInterceptor` | 1 o más (obligatorio) | Solo mensajes cuyos filtros coincidan |

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/mo-interceptors/` | Lista todos los interceptores MO |
| `GET` | `/mo-interceptors/{order}` | Obtiene un interceptor por su order |
| `POST` | `/mo-interceptors/` | Crea un interceptor nuevo |
| `PATCH` | `/mo-interceptors/{order}` | Actualiza el script o los filtros |
| `DELETE` | `/mo-interceptors/{order}` | Elimina un interceptor |
| `DELETE` | `/mo-interceptors/flush` | Elimina **todos** los interceptores MO |

---

## Parámetros

### POST `/mo-interceptors/` — Crear

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `type` | `string` | Sí | `"DefaultInterceptor"` o `"StaticMOInterceptor"` |
| `order` | `int` | Sí | Posición en la cadena. Menor = se ejecuta primero. |
| `filters` | `list[string]` | Solo en `StaticMOInterceptor` | Lista de FIDs de filtros que deben coincidir para que el interceptor aplique. |
| `script` | `string` | Sí | Código fuente Python. Debe ser un módulo válido. El objeto `routable` está disponible. |

### PATCH `/mo-interceptors/{order}` — Actualizar

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `filters` | `list[string] \| null` | Nueva lista de filtros. `null` = reutiliza los filtros actuales. |
| `script` | `string \| null` | Nuevo código Python. `null` = reutiliza el script en disco. |

### Respuesta (`InterceptorOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `order` | `int` | Posición en la cadena |
| `type` | `string` | Tipo de interceptor |
| `filters` | `list[string]` | Siempre `[]` |
| `script_path` | `string` | Ruta del script en disco (`/etc/jasmin/scripts/mo_{order}.py`) |

---

## El script Python

El script para interceptores MO funciona de la misma forma que en los interceptores MT. El objeto `routable` está disponible con la información del mensaje.

### Variables disponibles

| Variable | Descripción |
|----------|-------------|
| `routable.pdu.params['source_addr']` | Número del remitente (quien envió el SMS) |
| `routable.pdu.params['destination_addr']` | Número destino (el número del sistema) |
| `routable.pdu.params['short_message']` | Contenido del mensaje (bytes) |
| `routable.pdu.params['data_coding']` | Codificación del mensaje |

---

## Ejemplos de scripts

### Pass-through mínimo

```python
# MO pass-through — no modifica nada
```

### Normalizar número origen a E.164

```python
# Normalizar números mexicanos de 10 dígitos a formato +52...
src = routable.pdu.params.get('source_addr', b'').decode('ascii', errors='replace')
if src.isdigit() and len(src) == 10:
    routable.pdu.params['source_addr'] = f'+52{src}'.encode('ascii')
```

### Filtrar spam por contenido

```python
import re
content = routable.pdu.params.get('short_message', b'').decode('utf-8', errors='replace')
spam_patterns = [r'(?i)ganaste', r'(?i)premio', r'(?i)click aqui']
for pattern in spam_patterns:
    if re.search(pattern, content):
        raise Exception(f"Mensaje rechazado por spam: {pattern}")
```

### Logging de MO entrantes

```python
import logging
logger = logging.getLogger('jasmin.mo')
src = routable.pdu.params.get('source_addr', b'').decode('ascii', errors='replace')
dst = routable.pdu.params.get('destination_addr', b'').decode('ascii', errors='replace')
content = routable.pdu.params.get('short_message', b'').decode('utf-8', errors='replace')[:50]
logger.info(f"MO received: from={src} to={dst} content_preview={content!r}")
```

### Convertir UCS2 a UTF-8 si es necesario

```python
coding = routable.pdu.params.get('data_coding', 0)
if coding == 8:  # UCS2
    raw = routable.pdu.params.get('short_message', b'')
    try:
        text = raw.decode('utf-16-be')
        routable.pdu.params['short_message'] = text.encode('utf-8')
        routable.pdu.params['data_coding'] = 0
    except Exception:
        pass
```

---

## Ejemplos de endpoints

### Crear un DefaultInterceptor de normalización

```bash
curl -X POST https://api.example.com/api/v1/mo-interceptors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "DefaultInterceptor",
    "order": 0,
    "script": "src = routable.pdu.params.get(\"source_addr\", b\"\").decode(\"ascii\", errors=\"replace\")\nif src.isdigit() and len(src) == 10:\n    routable.pdu.params[\"source_addr\"] = f\"+52{src}\".encode(\"ascii\")\n"
  }'
```

### Crear un interceptor de anti-spam para contenido específico

```bash
# Crear el filtro de contenido spam
curl -X POST https://api.example.com/api/v1/filters/ \
  -H "X-API-Key: tu-api-key" -H "Content-Type: application/json" \
  -d '{"fid": "f_spam_pattern", "type": "ShortMessageFilter", "params": {"short_message": "(?i)(ganaste|premio|click aqui)"}}'

# Crear el interceptor que rechaza esos mensajes
curl -X POST https://api.example.com/api/v1/mo-interceptors/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "StaticMOInterceptor",
    "order": 5,
    "filters": ["f_spam_pattern"],
    "script": "raise Exception(\"Spam message rejected\")\n"
  }'
```

### Listar interceptores activos

```bash
curl https://api.example.com/api/v1/mo-interceptors/ \
  -H "X-API-Key: tu-api-key"
```

### Eliminar todos los interceptores MO (reset)

```bash
curl -X DELETE https://api.example.com/api/v1/mo-interceptors/flush \
  -H "X-API-Key: tu-api-key"
```

---

## Diferencias con interceptores MT

| Aspecto | MT Interceptors | MO Interceptors |
|---------|----------------|-----------------|
| Dirección | Mensajes salientes | Mensajes entrantes |
| Se ejecutan antes de | Las rutas MT (envío al carrier) | Las rutas MO (entrega al webhook) |
| Tipos | `DefaultInterceptor`, `StaticMTInterceptor` | `DefaultInterceptor`, `StaticMOInterceptor` |
| Script path | `/etc/jasmin/scripts/mt_{order}.py` | `/etc/jasmin/scripts/mo_{order}.py` |
| Variables de `routable` | Igual — mismo objeto PDU SMPP | Igual |

---

## Consideraciones de producción

- La API valida la sintaxis Python del script antes de enviarlo (retorna 422 si hay SyntaxError).
- El script no puede contener `return` a nivel de módulo (fuera de funciones).
- Los scripts se guardan en `/etc/jasmin/scripts/mo_{order}.py`. El archivo no se elimina al borrar el interceptor.
- Siempre probar el script en staging antes de aplicar en producción, especialmente los que rechazan mensajes.
- Los interceptores se ejecutan sincrónicamente dentro de Jasmin. Un script que tarda mucho (I/O de red, consultas lentas) bloquea el procesamiento de otros MO. Mantener los scripts simples y rápidos.

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | Error de Jasmin | Script falla al cargarse, campos faltantes |
| 400 | `Script file not found on disk...` | PATCH sin `script` y el archivo fue eliminado |
| 404 | `MO interceptor with order {order} not found` | El interceptor no existe |
| 409 | `MO interceptor with order {order} already exists` | Order duplicado |
| 422 | `Script is not valid Python: ...` | Error de sintaxis en el script |
| 503 | `Jasmin is not available` | Telnet desconectado |
