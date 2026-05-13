# Sistema (`/system`)

## Qué es

El módulo de sistema expone operaciones de control sobre la conexión entre la API y Jasmin, y sobre la persistencia de la configuración de Jasmin en disco.

No gestiona entidades (usuarios, rutas, etc.) — gestiona el **estado operativo** de Jasmin y del sidecar.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/system/persist` | Guarda la configuración actual de Jasmin en disco |
| `POST` | `/system/reload` | Recarga la configuración de Jasmin desde disco |
| `POST` | `/system/reconnect` | Reconecta la sesión Telnet con Jasmin |
| `GET` | `/system/session` | Estado actual de la sesión Telnet |

---

## Endpoints en detalle

### `POST /system/persist`

Ejecuta el comando `persist` en jcli de Jasmin. Guarda todas las entidades activas (rutas, interceptores, conectores, filtros, usuarios, grupos) en los archivos de perfil en disco (`/etc/jasmin/store/jcli-prod.*`).

**Sin persistencia, los cambios se pierden al reiniciar Jasmin.**

Jasmin trabaja en memoria por defecto — cada vez que creas una ruta, usuario o filtro via API, el cambio existe en memoria pero no en disco. Si Jasmin reinicia, esos cambios desaparecen a menos que se haya ejecutado `persist`.

```bash
curl -X POST https://api.example.com/api/v1/system/persist \
  -H "X-API-Key: tu-api-key"
```

Respuesta exitosa:
```json
{
  "data": "Persistence storage updated"
}
```

---

### `POST /system/reload`

Ejecuta el comando `load` en jcli de Jasmin. Recarga la configuración desde los archivos en disco, descartando cualquier cambio en memoria no persistido.

**Úsalo con cuidado:** los cambios no persistidos (via `persist`) se perderán.

```bash
curl -X POST https://api.example.com/api/v1/system/reload \
  -H "X-API-Key: tu-api-key"
```

---

### `POST /system/reconnect`

Fuerza la reconexión de la sesión Telnet del sidecar con Jasmin. Útil cuando la conexión Telnet se ha caído y el reconector automático no la ha restaurado aún.

En condiciones normales, el sidecar reconecta automáticamente. Este endpoint fuerza una reconexión inmediata.

```bash
curl -X POST https://api.example.com/api/v1/system/reconnect \
  -H "X-API-Key: tu-api-key"
```

---

### `GET /system/session`

Retorna el estado actual de la sesión Telnet entre el sidecar y Jasmin.

Respuesta (`SessionOut`):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connected` | `bool` | `true` si la sesión Telnet está activa |
| `reconnecting` | `bool` | `true` si el reconector automático está en proceso |
| `uptime_seconds` | `float \| null` | Segundos desde la última conexión exitosa. `null` si nunca conectó |
| `host` | `string` | Host de Jasmin al que conecta (de `JASMIN_TELNET_HOST`) |
| `port` | `int` | Puerto Telnet (de `JASMIN_TELNET_PORT`) |

```bash
curl https://api.example.com/api/v1/system/session \
  -H "X-API-Key: tu-api-key"
```

Ejemplo de respuesta:
```json
{
  "data": {
    "connected": true,
    "reconnecting": false,
    "uptime_seconds": 3600.5,
    "host": "127.0.0.1",
    "port": 8990
  }
}
```

---

## Flujo recomendado de trabajo

```
1. Crear/modificar entidades via API (rutas, usuarios, conectores, etc.)
2. Verificar que todo funciona correctamente
3. POST /system/persist → guardar en disco
4. (En caso de rollback) POST /system/reload → volver al último persist
```

---

## Cuándo usar `reload`

- Jasmin se reinició y recargó su configuración desde disco (más nueva que lo que tenía en memoria)
- Se hicieron cambios directos en los archivos de `/etc/jasmin/store/` y se quiere que Jasmin los tome
- Se quiere deshacer cambios en memoria que no se han persistido

---

## Errores posibles

| HTTP | Mensaje | Causa |
|------|---------|-------|
| 400 | Error de Jasmin | El comando no pudo ejecutarse (output inesperado) |
| 503 | `Jasmin is not available` | Sesión Telnet desconectada — usa `reconnect` primero |
