# Grupos (`/groups`)

## Qué son

Un grupo es un contenedor lógico de usuarios. Su función principal es permitir **habilitar o deshabilitar un conjunto de usuarios de forma colectiva**: cuando se deshabilita un grupo, todos los usuarios que pertenecen a él quedan bloqueados de enviar mensajes, sin tener que deshabilitar a cada usuario individualmente.

En el flujo de envío, Jasmin verifica si el grupo del usuario está habilitado antes de procesar el mensaje. Si el grupo está deshabilitado, el mensaje es rechazado aunque el usuario individual esté habilitado.

---

## Lugar en el flujo

```
Cliente → POST /sms/send
    → Jasmin autentica usuario
    → Jasmin verifica: ¿está el grupo del usuario habilitado?
         No → mensaje rechazado
         Sí → continúa con filtros de valor, rutas, etc.
```

Los grupos son el **primer nivel de control de acceso** después de la autenticación individual del usuario.

---

## Cuándo crear un grupo

- Cuando quieras poder pausar/reanudar un conjunto de usuarios con una sola operación (por ejemplo, suspender a todos los usuarios de un tenant sin eliminarlos).
- Cuando quieras aplicar políticas futuras a nivel de grupo (Jasmin puede extender el concepto).
- Como convención de organización: un grupo por tenant, por tipo de cuenta, por país, etc.

Un usuario **siempre** debe pertenecer a un grupo. No existe usuario sin grupo en Jasmin.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/groups/` | Lista todos los grupos |
| `GET` | `/groups/{gid}` | Obtiene un grupo específico |
| `POST` | `/groups/` | Crea un grupo nuevo |
| `PATCH` | `/groups/{gid}` | Habilita o deshabilita el grupo |
| `DELETE` | `/groups/{gid}` | Elimina el grupo |

---

## Parámetros

### POST `/groups/` — Crear

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `gid` | `string` | Sí | Identificador único del grupo en Jasmin. Sin espacios. Inmutable después de crear. |

**Restricciones de `gid`:**
- Longitud: 1–64 caracteres
- Sin espacios
- Sensible a mayúsculas (`premium` ≠ `Premium`)
- No puede modificarse después de creado; para cambiar el nombre hay que eliminar y recrear

### PATCH `/groups/{gid}` — Actualizar

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `enabled` | `boolean` | Sí | `true` = habilitar, `false` = deshabilitar |

### Respuesta (`GroupOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `gid` | `string` | Identificador del grupo |
| `enabled` | `boolean` | Estado actual |

---

## Ejemplos

### Crear un grupo

```bash
curl -X POST https://api.example.com/api/v1/groups/ \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"gid": "tenant_acme"}'
```

```json
{
  "success": true,
  "data": { "gid": "tenant_acme", "enabled": true },
  "message": "Group created"
}
```

### Deshabilitar un grupo (suspender todos sus usuarios)

```bash
curl -X PATCH https://api.example.com/api/v1/groups/tenant_acme \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Volver a habilitarlo

```bash
curl -X PATCH https://api.example.com/api/v1/groups/tenant_acme \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Eliminar un grupo

```bash
curl -X DELETE https://api.example.com/api/v1/groups/tenant_acme \
  -H "X-API-Key: tu-api-key"
```

---

## Restricciones y comportamiento especial

### No se puede eliminar un grupo con usuarios asignados

Jasmin rechaza la eliminación si existe al menos un usuario perteneciente al grupo. Debes eliminar o reasignar todos los usuarios primero.

```json
{
  "detail": {
    "msg": "Cannot remove group with assigned users",
    "type": "AppHttpException"
  }
}
```

### El GID es inmutable

No hay endpoint de renombrado. Para cambiar el `gid` de un grupo hay que:
1. Crear el nuevo grupo
2. Actualizar todos los usuarios (cambiar su `gid` al nuevo)
3. Eliminar el grupo anterior

### Creación idempotente

Jasmin acepta crear un grupo con un `gid` que ya existe sin devolver error. La API retorna 201 en ambos casos. No se genera error de conflicto (409) para grupos.

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 404 | `Group '{gid}' not found` | El grupo no existe en Jasmin |
| 409 | `Cannot remove group with assigned users` | Intento de eliminar grupo con usuarios |
| 503 | `Jasmin is not available` | La sesión Telnet con Jasmin está caída |
