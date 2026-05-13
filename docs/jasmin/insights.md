# Insights (`/insights`)

## Qué son

Los endpoints de Insights son **vistas compuestas de solo lectura** que combinan datos de dos o más módulos de Jasmin en una sola llamada. Están diseñados para alimentar dashboards, páginas de detalle y vistas de monitoreo en interfaces de administración, sin que el frontend tenga que orquestar múltiples requests independientes.

A diferencia de los endpoints base (`/users`, `/smpp-connectors`, etc.) que devuelven datos de un módulo, los insights devuelven información **cruzada y enriquecida**: configuración + estado en tiempo real + estadísticas históricas combinadas en un único objeto.

> **Todos los insights son de solo lectura.** No crean, modifican ni eliminan ningún recurso en Jasmin.

---

## Lugar en el flujo

```
Panel de administración / Dashboard
        │
        │  GET /insights/*  (una llamada)
        ▼
  jasmin-admin-api
        │
        ├── jcli Telnet ──► múltiples comandos combinados
        └── Jasmin HTTP ──► (solo para /overview)
```

El API ejecuta internamente los comandos jcli necesarios y los combina antes de responder. El cliente recibe un objeto completo en lugar de tener que hacer N llamadas y ensamblar los datos por su cuenta.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/insights/overview` | Conteos de todas las entidades + estado de salud del sistema |
| `GET` | `/insights/users/{uid}/profile` | Perfil completo de un usuario: configuración + grupo + estadísticas |
| `GET` | `/insights/groups/{gid}/members` | Miembros de un grupo con actividad en tiempo real |
| `GET` | `/insights/connectors/smpp/health` | Dashboard de salud de todos los conectores SMPP |
| `GET` | `/insights/connectors/smpp/{cid}/detail` | Vista completa de un conector SMPP: config + estado + stats |
| `GET` | `/insights/connectors/smpp/{cid}/usage` | Qué rutas MT dependen de un conector SMPP |
| `GET` | `/insights/sessions/active` | Snapshot en tiempo real de sesiones activas |
| `GET` | `/insights/routes/map` | Mapa topológico completo de todas las rutas MT y MO |

---

## Detalle de cada endpoint

---

### `GET /insights/overview`

**Combina:** `user --list` + `group --list` + `smppccm --list` + `httpccm --list` + `mtrouter --list` + `morouter --list` + `filter --list` + `mtinterceptor --list` + `mointerceptor --list` + probe HTTP

Devuelve un conteo de cada tipo de entidad en Jasmin más el estado de salud actual del sistema.

#### Respuesta (`OverviewOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | `string` | Estado global: `"ok"`, `"degraded"` o `"error"` |
| `telnet_connected` | `bool` | Si la sesión jcli está activa |
| `jasmin_http_reachable` | `bool` | Si la HTTP API de Jasmin responde |
| `counts.users` | `int` | Total de usuarios Jasmin |
| `counts.groups` | `int` | Total de grupos |
| `counts.smpp_connectors` | `int` | Total de conectores SMPP salientes |
| `counts.http_connectors` | `int` | Total de conectores HTTP (webhooks MO) |
| `counts.mt_routes` | `int` | Total de rutas MT activas |
| `counts.mo_routes` | `int` | Total de rutas MO activas |
| `counts.filters` | `int` | Total de filtros definidos |
| `counts.mt_interceptors` | `int` | Total de interceptores MT |
| `counts.mo_interceptors` | `int` | Total de interceptores MO |

#### Cuándo usarlo

- **Landing page del panel de administración**: primer endpoint que carga el dashboard para mostrar el estado general del sistema de un vistazo.
- **Widget de salud**: componente que indica si Jasmin está operando normalmente o en modo degradado.
- **Validación post-deploy**: confirmar que la cantidad esperada de recursos está configurada correctamente tras un despliegue.
- **Alerta de configuración vacía**: detectar que el sistema no tiene rutas o conectores configurados antes de intentar enviar SMS.

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/overview \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "status": "ok",
    "telnet_connected": true,
    "jasmin_http_reachable": true,
    "counts": {
      "users": 12,
      "groups": 3,
      "smpp_connectors": 4,
      "http_connectors": 2,
      "mt_routes": 6,
      "mo_routes": 1,
      "filters": 5,
      "mt_interceptors": 1,
      "mo_interceptors": 0
    }
  }
}
```

---

### `GET /insights/users/{uid}/profile`

**Combina:** `user -s {uid}` + `group -s {gid}` + `stats --user={uid}`

Devuelve en una sola llamada todo lo que se necesita para renderizar la página de detalle de un usuario: su configuración completa, el grupo al que pertenece y sus estadísticas de actividad en tiempo real.

Si el grupo no puede recuperarse (por ejemplo, Jasmin devuelve error) o si el usuario no tiene stats registradas, esos campos aparecen como `null` en lugar de fallar toda la respuesta.

#### Respuesta (`UserProfileOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user` | `UserOut` | Configuración completa del usuario (quotas, auth flags, filtros de valor) |
| `group` | `GroupOut \| null` | Grupo al que pertenece; `null` si no puede recuperarse |
| `stats` | `UserStatsOut \| null` | Estadísticas en tiempo real de actividad SMPP y HTTP |

Ver documentación de `/users` y `/stats/users/{uid}` para el detalle de cada campo.

#### Cuándo usarlo

- **Página de detalle de usuario**: renderizar toda la información de un usuario sin encadenar tres llamadas desde el frontend.
- **Diagnóstico de un usuario específico**: ver simultáneamente si un usuario está habilitado, a qué grupo pertenece, qué cuotas tiene y cuánta actividad ha tenido.
- **Soporte técnico**: cuando un cliente reporta que no puede enviar mensajes, una sola llamada muestra si está deshabilitado, sin balance, sin cuota de SMS o sin actividad reciente.
- **Auditoría**: verificar que la configuración de autorizaciones (`mt_auth_*`) y filtros de valor coincide con lo esperado para ese usuario.

#### Comportamiento ante errores parciales

| Situación | Resultado |
|-----------|-----------|
| Usuario no existe | `404 Not Found` — falla completa |
| Grupo no recuperable | `group: null` — el resto del perfil se devuelve igualmente |
| Stats no disponibles | `stats: null` — el resto del perfil se devuelve igualmente |

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/users/tenant_acme_01/profile \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "user": {
      "uid": "tenant_acme_01",
      "gid": "premium",
      "username": "acme_api",
      "enabled": true,
      "balance": 250.0,
      "sms_count": null,
      "mt_throughput": 10.0
    },
    "group": {
      "gid": "premium",
      "enabled": true
    },
    "stats": {
      "uid": "tenant_acme_01",
      "http_connects_count": 142,
      "http_submit_sm_request_count": 138,
      "http_last_activity_at": "2026-05-13 14:22:01"
    }
  }
}
```

---

### `GET /insights/groups/{gid}/members`

**Combina:** `group -s {gid}` + `user --list` (filtrado por gid) + `stats --users`

Devuelve el grupo y todos los usuarios que pertenecen a él, enriquecidos con sus estadísticas de actividad reciente (conexiones SMPP activas, requests HTTP). Ejecuta exactamente dos comandos jcli independientemente de cuántos miembros tenga el grupo.

#### Respuesta (`GroupMembersOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `group` | `GroupOut` | Configuración del grupo (gid, enabled) |
| `members` | `list[GroupMemberOut]` | Usuarios del grupo con actividad |
| `total` | `int` | Cantidad total de miembros |

#### `GroupMemberOut`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `uid` | `string` | ID del usuario |
| `enabled` | `bool` | Si el usuario está habilitado |
| `smpp_bound_connections` | `int` | Conexiones SMPP actualmente activas |
| `http_request_count` | `int` | Total de requests HTTP realizados |
| `smpp_last_activity` | `string \| null` | Última actividad vía SMPP |
| `http_last_activity` | `string \| null` | Última actividad vía HTTP |

#### Cuándo usarlo

- **Página de detalle de grupo**: mostrar quiénes pertenecen al grupo y cuáles están activos en este momento.
- **Auditoría de grupos**: identificar usuarios inactivos (sin actividad reciente y sin conexiones) que podrían limpiarse.
- **Gestión multi-tenant**: cuando cada grupo representa un cliente/tenant, esta vista permite ver todos los usuarios de ese tenant de un vistazo.
- **Antes de deshabilitar un grupo**: verificar si alguno de sus miembros tiene sesiones SMPP activas (`smpp_bound_connections > 0`) que se verían interrumpidas.
- **Soporte**: identificar rápidamente qué usuarios de un cliente están generando actividad versus cuáles están inactivos.

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/groups/premium/members \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "group": { "gid": "premium", "enabled": true },
    "members": [
      {
        "uid": "tenant_acme_01",
        "enabled": true,
        "smpp_bound_connections": 2,
        "http_request_count": 142,
        "smpp_last_activity": "2026-05-13 14:20:00",
        "http_last_activity": "2026-05-13 14:22:01"
      },
      {
        "uid": "tenant_beta_01",
        "enabled": false,
        "smpp_bound_connections": 0,
        "http_request_count": 0,
        "smpp_last_activity": null,
        "http_last_activity": null
      }
    ],
    "total": 2
  }
}
```

---

### `GET /insights/connectors/smpp/health`

**Combina:** `smppccm --list` + `stats --smppcs`

Devuelve todos los conectores SMPP con su estado operacional actual y sus métricas de submits/errores en una sola llamada. Incluye contadores de resumen: total de conectores, cuántos están activamente conectados y cuántos presentan errores.

#### Respuesta (`SmppConnectorsHealthOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connectors` | `list[SmppConnectorHealthEntry]` | Una entrada por conector |
| `total` | `int` | Total de conectores configurados |
| `connected` | `int` | Conectores con `sessions_count > 0` (activamente bound) |
| `with_errors` | `int` | Conectores con al menos un error de QoS u otro error |

#### `SmppConnectorHealthEntry`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cid` | `string` | ID del conector |
| `status` | `string` | Estado actual: `started`, `stopped`, `bound_TRX`, etc. |
| `sessions_count` | `int` | Sesiones SMPP activas ahora mismo |
| `connected_at` | `string \| null` | Última conexión TCP al carrier |
| `bound_at` | `string \| null` | Último bind SMPP exitoso |
| `disconnected_at` | `string \| null` | Última desconexión |
| `submits` | `string` | `"enviados/intentados"` — e.g. `"980/1000"` |
| `delivers` | `string` | `"entregados/intentados"` |
| `qos_errors` | `int` | Errores de throttling del carrier |
| `other_errors` | `int` | Otros errores de submit_sm |

#### Cuándo usarlo

- **Dashboard principal de carriers**: tabla que muestra de un vistazo el estado de salud de cada conector con sus métricas clave.
- **Monitoreo en producción**: detectar inmediatamente si algún conector está desconectado o generando errores sin tener que revisar cada uno por separado.
- **Alertas y NOC**: el campo `with_errors` permite construir alertas rápidas: si `with_errors > 0` hay al menos un carrier con problemas.
- **Comparación entre carriers**: ver cuál carrier tiene mejor tasa de éxito (`submits`) para optimizar las rutas.
- **Estado post-mantenimiento**: verificar que todos los conectores se reconectaron correctamente después de un reinicio de Jasmin.

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/connectors/smpp/health \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "connectors": [
      {
        "cid": "carrier_mx",
        "status": "bound_TRX",
        "sessions_count": 1,
        "connected_at": "2026-05-13 08:00:12",
        "bound_at": "2026-05-13 08:00:13",
        "disconnected_at": null,
        "submits": "4820/4850",
        "delivers": "4750/4820",
        "qos_errors": 0,
        "other_errors": 30
      },
      {
        "cid": "carrier_us",
        "status": "stopped",
        "sessions_count": 0,
        "connected_at": null,
        "bound_at": null,
        "disconnected_at": "2026-05-12 23:15:00",
        "submits": "0/0",
        "delivers": "0/0",
        "qos_errors": 0,
        "other_errors": 0
      }
    ],
    "total": 2,
    "connected": 1,
    "with_errors": 1
  }
}
```

---

### `GET /insights/connectors/smpp/{cid}/detail`

**Combina:** `smppccm -s {cid}` + `smppccm --list` (estado actual) + `stats --smppc={cid}`

Devuelve la vista completa de un conector SMPP específico: su configuración técnica completa, el estado operacional en tiempo real (iniciado/detenido/bound, sesiones activas) y todos sus contadores históricos de actividad. Reemplaza tres llamadas separadas a `/smpp-connectors/{cid}`, `/smpp-connectors/{cid}/status` y `/stats/smpp-connectors/{cid}`.

Si las estadísticas no están disponibles (conector recién creado, Jasmin sin stats para ese CID), el campo `stats` aparece como `null` en lugar de fallar la respuesta completa.

#### Respuesta (`SmppConnectorDetailOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `connector` | `SmppConnectorOut` | Configuración completa (host, port, TON/NPI, throughput, reconexión) |
| `status` | `SmppConnectorStatusOut` | Estado actual (status, sessions_count) |
| `stats` | `SmppConnectorStatsOut \| null` | Contadores históricos (submits, errores, timestamps) |

Ver documentación de `/smpp-connectors` y `/stats/smpp-connectors/{cid}` para el detalle de cada subcampo.

#### Cuándo usarlo

- **Página de detalle de un conector**: renderizar toda la información del conector en una sola llamada en lugar de tres.
- **Diagnóstico de conectividad**: cuando un carrier reporta problemas, ver en un vistazo si está bound, cuándo fue la última conexión exitosa y cuántos errores acumula.
- **Análisis de rendimiento de un carrier**: revisar el throughput configurado vs. la tasa real de submits aceptados.
- **Validación de configuración**: confirmar que TON/NPI, system_type y demás parámetros técnicos están correctamente aplicados antes de iniciar el conector.
- **Vista de soporte**: cuando se escala un incidente de entrega, esta vista provee todo el contexto técnico del canal afectado.

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/connectors/smpp/carrier_mx/detail \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "connector": {
      "cid": "carrier_mx",
      "host": "smpp.carrier.com",
      "port": 2775,
      "username": "acme_esme",
      "bind_to": "transceiver",
      "submit_throughput": 50.0,
      "reconnect_on_connection_loss": true
    },
    "status": {
      "cid": "carrier_mx",
      "status": "bound_TRX",
      "sessions_count": 1,
      "last_error": null
    },
    "stats": {
      "cid": "carrier_mx",
      "connected_at": "2026-05-13 08:00:12",
      "bound_at": "2026-05-13 08:00:13",
      "submit_sm_request_count": 4850,
      "submit_sm_count": 4820,
      "throttling_error_count": 0,
      "other_submit_error_count": 30
    }
  }
}
```

---

### `GET /insights/connectors/smpp/{cid}/usage`

**Combina:** `smppccm -s {cid}` + `mtrouter --list` + `mtrouter -s {order}` (por cada ruta)

Devuelve la configuración del conector y todas las rutas MT que lo referencian. Para cada ruta coincidente muestra el orden de evaluación, el tipo de ruta y la tarifa por mensaje.

#### Respuesta (`SmppConnectorUsageOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cid` | `string` | ID del conector consultado |
| `connector` | `SmppConnectorOut` | Configuración completa del conector |
| `mt_routes` | `list[ConnectorRouteRef]` | Rutas MT que apuntan a este conector |
| `mt_routes_count` | `int` | Cantidad total de rutas que lo usan |

#### `ConnectorRouteRef`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `order` | `int` | Orden de evaluación de la ruta (menor = mayor prioridad) |
| `type` | `string` | Tipo de ruta (`DefaultRoute`, `StaticMTRoute`, etc.) |
| `rate` | `float \| null` | Tarifa por mensaje configurada en esa ruta |

#### Cuándo usarlo

- **Antes de modificar un conector**: verificar cuántas y cuáles rutas dependen de él para estimar el impacto de un cambio de configuración.
- **Antes de eliminar un conector**: si `mt_routes_count > 0`, eliminarlo dejará esas rutas sin destino y los mensajes comenzarán a fallar. Este endpoint permite identificar qué rutas hay que reasignar primero.
- **Análisis de dependencias de carrier**: entender qué tráfico fluye por cada carrier (rutas con tarifa alta = tráfico premium, DefaultRoute = tráfico general).
- **Validación de routing**: confirmar que un conector recién creado ya fue asociado a al menos una ruta activa.
- **Planificación de migración**: al mover tráfico de un carrier a otro, identificar todas las rutas que apuntan al conector origen para redirigirlas sistemáticamente.

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/connectors/smpp/carrier_mx/usage \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "cid": "carrier_mx",
    "connector": { "cid": "carrier_mx", "host": "smpp.carrier.com", "port": 2775 },
    "mt_routes": [
      { "order": 0,  "type": "DefaultRoute",  "rate": 0.05 },
      { "order": 10, "type": "StaticMTRoute", "rate": 0.10 }
    ],
    "mt_routes_count": 2
  }
}
```

---

### `GET /insights/sessions/active`

**Combina:** `stats --users` + `stats --smppcs` + `smppccm --list` + `stats --smppsapi`

Snapshot en tiempo real de todo lo que está activo en Jasmin ahora mismo: usuarios con sesiones SMPP bound, conectores que están iniciados o conectados al carrier, y el estado global del servidor SMPP inbound.

- **Usuarios activos**: solo los que tienen `smpp_bound_connections > 0` en el momento de la consulta.
- **Conectores activos**: todos los que tienen status diferente de `stopped` o tienen `sessions_count > 0`.

#### Respuesta (`ActiveSessionsOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `active_users` | `list[ActiveUserSession]` | Usuarios con al menos una conexión SMPP activa |
| `active_connectors` | `list[ActiveConnectorSession]` | Conectores en estado no detenido |
| `smpp_server` | `SmppServerApiStatsOut` | Estado del servidor SMPP de Jasmin (inbound) |
| `total_bound_users` | `int` | Cantidad de usuarios activos en este momento |
| `total_connected_connectors` | `int` | Cantidad de conectores activos en este momento |

#### `ActiveUserSession`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `uid` | `string` | ID del usuario |
| `smpp_bound_connections` | `int` | Sesiones SMPP activas ahora mismo |
| `smpp_last_activity` | `string \| null` | Última actividad SMPP |
| `http_request_count` | `int` | Total histórico de requests HTTP |
| `http_last_activity` | `string \| null` | Última actividad HTTP |

#### `ActiveConnectorSession`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cid` | `string` | ID del conector |
| `status` | `string` | Estado actual (`started`, `bound_TRX`, `connecting`, etc.) |
| `sessions_count` | `int` | Sesiones SMPP activas con el carrier |
| `bound_at` | `string \| null` | Cuándo fue el último bind exitoso |
| `submits` | `string` | Submits enviados/intentados en esta sesión |

#### Cuándo usarlo

- **Vista de monitoreo en vivo (NOC)**: widget de "actividad ahora mismo" que muestra cuántos clientes y carriers están conectados en este instante.
- **Diagnóstico de caídas**: si se detecta que los mensajes dejan de llegar, este endpoint permite confirmar inmediatamente si los conectores se desconectaron o si los usuarios perdieron sus sesiones.
- **Verificación post-reinicio de Jasmin**: confirmar que los conectores se reconectaron y los clientes SMPP volvieron a hacer bind después de un reinicio.
- **Capacidad actual**: ver cuántos bind slots están en uso para planificar si se necesita aumentar `smpps_max_bindings`.
- **Detección de sesiones fantasma**: identificar usuarios con conexiones activas cuyos sistemas deberían estar offline (por ejemplo, tras un mantenimiento del cliente).

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/sessions/active \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "active_users": [
      {
        "uid": "tenant_acme_01",
        "smpp_bound_connections": 2,
        "smpp_last_activity": "2026-05-13 14:20:00",
        "http_request_count": 142,
        "http_last_activity": "2026-05-13 14:22:01"
      }
    ],
    "active_connectors": [
      {
        "cid": "carrier_mx",
        "status": "bound_TRX",
        "sessions_count": 1,
        "bound_at": "2026-05-13 08:00:13",
        "submits": "4820/4850"
      }
    ],
    "smpp_server": {
      "connected_count": 2,
      "bound_trx_count": 2,
      "submit_sm_request_count": 280
    },
    "total_bound_users": 1,
    "total_connected_connectors": 1
  }
}
```

---

### `GET /insights/routes/map`

**Combina:** `mtrouter --list` + `mtrouter -s {order}` (por cada ruta MT) + `morouter --list` + `morouter -s {order}` (por cada ruta MO)

Devuelve la topología completa de enrutamiento de Jasmin: todas las rutas MT y MO con sus conectores de destino y los indicadores de filtro, ordenadas tal como Jasmin las evalúa. El campo `filter_indicator` muestra el indicador raw de Jasmin para el filtro asignado (`<T>` = TransparentFilter; valor vacío = sin filtro, como en DefaultRoute).

> **Nota sobre filtros:** Jasmin no expone los FIDs de filtro en el output de detalle de ruta (`-s`), por lo que `filter_indicator` es un indicador visual derivado del listado, no el FID recuperable. Las rutas siempre devuelven `filters: []` en los endpoints base por la misma razón.

#### Respuesta (`RouteMapOut`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `mt_routes` | `list[MtRouteMapEntry]` | Rutas MT en orden de evaluación |
| `mo_routes` | `list[MoRouteMapEntry]` | Rutas MO en orden de evaluación |
| `total_mt` | `int` | Total de rutas MT |
| `total_mo` | `int` | Total de rutas MO |

#### `MtRouteMapEntry`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `order` | `int` | Prioridad de evaluación (menor = mayor prioridad) |
| `type` | `string` | Tipo de ruta (`DefaultRoute`, `StaticMTRoute`, `RandomRoundrobinMTRoute`) |
| `connectors` | `list[string]` | Conectores de destino con prefijo (`smppc(cid)`) |
| `filter_indicator` | `string` | Indicador de filtro: `<T>` = TransparentFilter, `""` = sin filtro |
| `rate` | `float \| null` | Tarifa por mensaje de esta ruta |

#### `MoRouteMapEntry`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `order` | `int` | Prioridad de evaluación |
| `type` | `string` | Tipo de ruta (`DefaultRoute`, `StaticMORoute`) |
| `connector` | `string` | Conector HTTP de destino con prefijo (`http(cid)`) |
| `filter_indicator` | `string` | Indicador de filtro |

#### Cuándo usarlo

- **Visualización de topología de routing**: renderizar un diagrama que muestre el flujo completo desde un mensaje entrante hasta su carrier de destino, incluyendo todos los niveles de prioridad.
- **Auditoría de routing**: verificar que las reglas de enrutamiento están configuradas correctamente: qué ruta tiene más prioridad, qué conector recibe el tráfico por defecto.
- **Planificación de cambios**: antes de modificar rutas, ver el mapa completo para entender el impacto en cascada.
- **Verificación de que no hay rutas huérfanas**: identificar rutas que apuntan a conectores con errores o detenidos (cruzando con `/insights/connectors/smpp/health`).
- **Documentación automática**: generar automáticamente la documentación de la configuración de routing del sistema en un momento dado.
- **Troubleshooting de entrega**: cuando un mensaje no llega, esta vista permite trazar manualmente qué ruta se habría evaluado primero y hacia qué carrier habría ido.

#### Ejemplo

```bash
curl https://api.example.com/api/v1/insights/routes/map \
  -H "X-API-Key: tu-api-key"
```

```json
{
  "data": {
    "mt_routes": [
      {
        "order": 10,
        "type": "StaticMTRoute",
        "connectors": ["smppc(carrier_premium)"],
        "filter_indicator": "<T>",
        "rate": 0.10
      },
      {
        "order": 0,
        "type": "DefaultRoute",
        "connectors": ["smppc(carrier_mx)"],
        "filter_indicator": "",
        "rate": 0.05
      }
    ],
    "mo_routes": [
      {
        "order": 0,
        "type": "DefaultRoute",
        "connector": "http(webhook_crm)",
        "filter_indicator": ""
      }
    ],
    "total_mt": 2,
    "total_mo": 1
  }
}
```

---

## Errores posibles (todos los endpoints)

| HTTP | Mensaje | Causa |
|------|---------|-------|
| `404` | `User '{uid}' not found` | El UID no existe en Jasmin |
| `404` | `Group '{gid}' not found` | El GID no existe en Jasmin |
| `404` | `SMPP connector '{cid}' not found` | El CID no existe en Jasmin |
| `503` | `Jasmin is not available` | La sesión Telnet jcli está desconectada |

Los endpoints con datos opcionales (`user/profile`, `connectors/smpp/{cid}/detail`) **no fallan** si solo una parte de la información no está disponible — devuelven `null` en esos campos y retornan `200` con el resto de los datos.

---

## Consideraciones de rendimiento

Cada endpoint de insights ejecuta múltiples comandos jcli internamente. Dado que **jcli es single-threaded**, los comandos se serializan uno por uno:

| Endpoint | Comandos jcli ejecutados |
|----------|--------------------------|
| `/overview` | 9 comandos (uno por tipo de entidad) + 1 probe HTTP |
| `/users/{uid}/profile` | 3 comandos |
| `/groups/{gid}/members` | 2 comandos |
| `/connectors/smpp/health` | 2 comandos |
| `/connectors/smpp/{cid}/detail` | 3 comandos |
| `/connectors/smpp/{cid}/usage` | 1 + N (una llamada show por cada ruta MT) |
| `/sessions/active` | 4 comandos |
| `/routes/map` | 2 + N·MT + N·MO (una llamada show por cada ruta) |

Para instalaciones con muchas rutas (más de 50), `/routes/map` y `/connectors/smpp/{cid}/usage` pueden tardar varios segundos. Se recomienda aplicar caché en el frontend para estas vistas o invocarlas bajo demanda en lugar de actualizarlas en polling frecuente.
