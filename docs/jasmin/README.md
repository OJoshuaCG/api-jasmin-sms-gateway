# Jasmin SMS Gateway — Documentación de Módulos

Esta carpeta documenta cada módulo administrable de Jasmin a través de la API REST del sidecar. Cada archivo describe el propósito del módulo, sus parámetros, valores permitidos, ejemplos de uso y su lugar en el flujo operacional.

---

## Índice

| Módulo | Archivo | Descripción breve |
|--------|---------|-------------------|
| Grupos | [groups.md](./groups.md) | Agrupan usuarios para aplicar políticas colectivas |
| Usuarios | [users.md](./users.md) | Credenciales y límites de acceso al gateway |
| Conectores SMPP | [smpp-connectors.md](./smpp-connectors.md) | Conexiones salientes al carrier/SMSC |
| Conectores HTTP | [http-connectors.md](./http-connectors.md) | Destinos de entrega de mensajes entrantes (MO) |
| Filtros | [filters.md](./filters.md) | Condiciones de selección de mensajes |
| Rutas MT | [mt-routes.md](./mt-routes.md) | Hacia dónde se envían los mensajes salientes |
| Rutas MO | [mo-routes.md](./mo-routes.md) | Hacia dónde se entregan los mensajes entrantes |
| Interceptores MT | [mt-interceptors.md](./mt-interceptors.md) | Scripts Python sobre mensajes salientes antes de enrutar |
| Interceptores MO | [mo-interceptors.md](./mo-interceptors.md) | Scripts Python sobre mensajes entrantes antes de entregar |
| SMS | [sms.md](./sms.md) | Envío de mensajes, consulta de balance y tarifa |
| Estadísticas | [stats.md](./stats.md) | Métricas en tiempo real de conectores, usuarios y APIs |
| Servidor SMPP | [smpp-server.md](./smpp-server.md) | Configuración del servidor SMPP inbound de Jasmin |
| Sistema | [system.md](./system.md) | Persistencia, recarga y estado de la sesión Telnet |

---

## Arquitectura general

```
Cliente (app, orchestrator)
        │
        │  HTTP + X-API-Key
        ▼
  jasmin-admin-api  :8080
        │
        ├── Telnet localhost:8990 ──► jcli (administración)
        └── HTTP   localhost:1401 ──► /send, /rate (envío de SMS)
                        │
                  Jasmin SMS Gateway
                        │
            ┌───────────┼───────────┐
            │           │           │
      SMPP Connector  SMPP Server  Jasmin DB
      (outbound →     (inbound ←   (config en disco)
       carrier)        resellers)
```

El sidecar es el **único punto de entrada** a Jasmin. Los puertos Telnet (8990) y HTTP (1401) nunca se exponen al exterior.

---

## Flujo de un mensaje saliente (MT — Mobile Terminated)

Un mensaje enviado por un cliente de la plataforma hacia un número de celular:

```
1. Cliente llama a POST /sms/send
        │
2. Sidecar proxea a Jasmin HTTP API (localhost:1401)
        │
3. Jasmin autentica al usuario (uid + password)
        │
4. Jasmin aplica value filters del usuario
   (¿el src_addr cumple el regex? ¿tiene balance?)
        │
5. Jasmin evalúa MT Interceptors (orden ascendente)
   Script Python puede modificar o rechazar el mensaje
        │
6. Jasmin evalúa MT Routes (orden ascendente)
   Primera ruta cuyo filtro coincide gana
        │
7. Jasmin envía el mensaje por el SMPP Connector
   de la ruta ganadora → Carrier/SMSC
        │
8. Carrier retorna un SMPP message_id
        │
9. Sidecar retorna { "message_id": "..." } al cliente
        │
10. (Asíncrono) Carrier envía DLR → Jasmin →
    Jasmin hace POST al dlr_url del cliente
```

---

## Flujo de un mensaje entrante (MO — Mobile Originated)

Un SMS enviado por un usuario final desde su celular hacia un número del sistema:

```
1. Usuario final envía SMS al número del carrier
        │
2. Carrier entrega el mensaje al SMPP Connector
   de Jasmin (inbound bind)
        │
3. Jasmin evalúa MO Interceptors (orden ascendente)
   Script Python puede modificar o rechazar el mensaje
        │
4. Jasmin evalúa MO Routes (orden ascendente)
   Primera ruta cuyo filtro coincide gana
        │
5. Jasmin entrega el mensaje al HTTP Connector
   de la ruta ganadora → hace GET o POST a la URL configurada
        │
6. La aplicación receptora procesa el MO
```

---

## Jerarquía de dependencias

Para configurar el gateway correctamente, los recursos deben crearse en este orden:

```
1. Grupos          (prerequisito de Usuarios)
2. Usuarios        (credenciales de envío)
3. Filtros         (prerequisito de Rutas e Interceptores con filtros)
4. Conectores SMPP (prerequisito de Rutas MT)
5. Conectores HTTP (prerequisito de Rutas MO)
6. Rutas MT        (necesita Conectores SMPP + Filtros)
7. Rutas MO        (necesita Conectores HTTP + Filtros)
8. Interceptores   (opcionales; necesitan Filtros si son Static*)
```

---

## Convenciones de la API

### Autenticación

Todos los endpoints requieren el header:
```
X-API-Key: <tu-api-key>
```

### Formato de respuesta

**Éxito con datos:**
```json
{
  "success": true,
  "data": { ... },
  "message": "opcional"
}
```

**Error:**
```json
{
  "detail": {
    "msg": "Descripción del error",
    "type": "AppHttpException"
  }
}
```

### Códigos HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK |
| 201 | Creado |
| 400 | Parámetros inválidos o error de Jasmin |
| 401 | API Key faltante o inválida |
| 404 | Recurso no encontrado |
| 409 | Conflicto (ya existe) |
| 422 | Error de validación (schema Pydantic) |
| 503 | Jasmin no disponible (Telnet desconectado) |

### IDs de conectores en rutas

Cuando una ruta referencia un conector, se usa el prefijo del tipo:

| Tipo de conector | Sintaxis en rutas |
|-----------------|-------------------|
| SMPP outbound | `smppc(<cid>)` |
| HTTP | `http(<cid>)` |
| SMPP Server (inbound) | `smpps(<cid>)` |

Ejemplo: si tienes un SMPP connector con `cid = "carrier_mx"`, en una ruta MT usas `"smppc(carrier_mx)"`.

---

## Comportamiento de persist

Jasmin almacena su configuración en archivos en disco. Los cambios hechos vía jcli existen solo en memoria hasta ejecutar `persist`. El sidecar ejecuta `persist` automáticamente después de **cada operación de escritura exitosa**. Si `persist` falla, la operación completa se considera fallida.

Esto significa que si el servidor pierde energía justo después de que el sidecar confirma una operación, la configuración en disco ya fue guardada y sobrevive el reinicio.
