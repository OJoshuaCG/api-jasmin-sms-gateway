# jasmin-admin-api — Contexto y Arquitectura

> Documento: contexto técnico del servicio `jasmin-admin-api`
> Creado: 2026-05-02
> Relacionado: `plans/004_sms-channel/013_jasmin-admin-api.md`

---

## El problema

Jasmin SMS Gateway expone tres interfaces:

| Interfaz | Puerto | Para qué |
|---|---|---|
| Telnet CLI (jcli) | 8990 | Administración completa del gateway |
| HTTP API | 1401 | Envío de mensajes (MT) |
| SMPP Server | 2775 | Recibir conexiones de resellers |

Para que cualquier sistema externo pueda administrar Jasmin o enviar mensajes a través de él, necesita acceso directo a esos puertos. Eso crea tres problemas concretos:

**1. El puerto Telnet (8990) no tiene seguridad real.**
jcli autentica con usuario y contraseña, pero el protocolo es texto plano. Cualquier sistema que quiera administrar Jasmin debe tener acceso de red a ese puerto. Si ese puerto es accesible desde fuera del servidor, cualquier actor con las credenciales puede tomar control total del gateway — agregar rutas, modificar usuarios, detener conectores.

**2. El jcli no es una API — es una interfaz de línea de comandos.**
Sus respuestas son texto libre diseñado para ser leído por un humano, no por un programa. Quien quiera consumirlo programáticamente tiene que:
- Mantener una sesión Telnet activa y reconectarla si cae
- Serializar todos los comandos (jcli solo acepta uno a la vez por sesión)
- Parsear texto como `"Success: 1 Filter(s) in memory"` para saber si algo funcionó
- Manejar prompts interactivos (`jcli>`, `Username:`, etc.)

Esa lógica es frágil, difícil de testear, y si se distribuye en múltiples servicios (orchestrator, worker, admin panel) se duplica y diverge.

**3. La HTTP API de Jasmin tampoco debe estar expuesta directamente.**
Es el endpoint para enviar SMS. Si está accesible desde fuera del servidor, cualquier sistema podría enviar mensajes usando las credenciales de un usuario Jasmin, sin pasar por los controles del sistema UCaaS (billing, rate limiting, auditoría).

---

## La solución

Se crea un servicio llamado **`jasmin-admin-api`** que vive en el mismo servidor o pod que Jasmin y actúa como su única interfaz de acceso al exterior.

```
                    ┌──────────────────────────────────────────┐
                    │         Servidor / Pod Jasmin            │
                    │                                          │
Sistema UCaaS  ───► │  jasmin-admin-api  :8100  (REST + Auth) │
  Orchestrator      │         │                                │
  Admin panel       │         ├── Telnet localhost:8990 ──► jcli
  Cualquier         │         └── HTTP  localhost:1401  ──► /send, /rate
  cliente HTTP      │                                          │
                    │         Jasmin SMS Gateway               │
                    └──────────────────────────────────────────┘
```

`jasmin-admin-api` hace tres cosas:

1. **Encapsula jcli**: traduce llamadas REST a comandos Telnet y devuelve JSON estructurado.
2. **Proxea la HTTP API de Jasmin**: el cliente llama a `/sms/send` en el sidecar; el sidecar llama a Jasmin internamente.
3. **Añade autenticación**: todos los endpoints requieren una API Key. Jasmin en sí no sabe quién llama.

Resultado: Jasmin no expone ningún puerto al exterior. Solo el puerto 8100 del sidecar es accesible desde la red, y ese puerto está protegido.

---

## Qué cubre

El sidecar implementa acceso completo a todos los componentes administrables de Jasmin:

| Módulo | qué es en Jasmin | CRUD |
|---|---|---|
| **Groups** | Grupos de usuarios (`group`) | Completo |
| **Users** | Usuarios de la HTTP API de Jasmin (`user`) | Completo + enable/disable |
| **SMPP Connectors** | Conectores SMPP outbound a carriers (`smppccm`) | Completo + start/stop/status |
| **HTTP Connectors** | Destinos de entrega de MO (`httpccm`) | Completo |
| **Filters** | Filtros por origen, destino, contenido, horario, etc. (`filter`) | Completo |
| **MT Routes** | Rutas de salida — a qué conector va cada mensaje (`mtrouter`) | Completo + flush |
| **MO Routes** | Rutas de entrada — a qué URL van los MO recibidos (`morouter`) | Completo + flush |
| **MT Interceptors** | Scripts Python que procesan mensajes antes de enviarlos (`mtinterceptor`) | Completo + flush |
| **MO Interceptors** | Scripts Python que procesan MO antes de entregarlos (`mointerceptor`) | Completo + flush |
| **SMPP Server** | Configuración del servidor SMPP interno de Jasmin (`smppserver`) | Lectura + update |
| **Stats** | Métricas en tiempo real de conectores y usuarios (`stats`) | Solo lectura |
| **Sistema** | Persist, reload, reconexión, health check | Operaciones admin |
| **SMS Send** | Proxy de `/send` y `/rate` de Jasmin | Proxy completo |

---

## Qué NO cubre

- **No administra la base de datos UCaaS.** El sidecar no lee ni escribe en `sms_infrastructure` ni `sms_tenant`. Solo habla con Jasmin. La sincronización entre la DB y el estado de Jasmin es responsabilidad del orchestrator.
- **No procesa DLR callbacks.** Los DLR los sigue recibiendo el orchestrator directamente desde Jasmin (Jasmin hace POST al webhook del orchestrator). El sidecar no está en ese camino.
- **No gestiona múltiples instancias Jasmin.** Cada sidecar administra exactamente un Jasmin — el que corre en el mismo servidor. Para múltiples instancias Jasmin, se despliegan múltiples sidecars.
- **No persiste estado propio.** No tiene base de datos. El estado real está en Jasmin. El sidecar es stateless excepto por la sesión Telnet activa.
- **No implementa lógica de negocio.** No sabe qué es un tenant, un plan, un límite de mensajes, ni tarifas. Todo eso lo maneja el orchestrator.
- **No reemplaza el SMPP Server de Jasmin.** El puerto 2775 para conexiones SMPP de resellers sigue siendo directo — eso no pasa por el sidecar.

---

## Cómo funciona internamente

### Sesión Telnet

Al arrancar, el sidecar establece una conexión Telnet persistente a `localhost:8990` y se autentica con las credenciales jcli configuradas en sus variables de entorno. Esa sesión se mantiene activa durante toda la vida del proceso.

**El jcli de Jasmin acepta solo un comando a la vez por sesión.** Esto es una limitación del diseño de Jasmin: es un servidor Telnet construido sobre Python/Twisted que procesa comandos secuencialmente. Si dos requests llegan al sidecar simultáneamente, el segundo espera en cola hasta que el primero termine. No hay timeout de espera por defecto en la cola — solo hay timeout por comando individual (configurable, default 10 segundos).

Flujo de un comando típico:
```
Request HTTP → sidecar
    → adquirir lock de sesión Telnet
    → enviar comando: "mtrouter --add -t StaticMTRoute -r 10 -f f1 -c smpp-01"
    → esperar prompt "jcli>"
    → leer respuesta
    → ejecutar "persist"
    → esperar prompt "jcli>"
    → liberar lock
    → parsear respuesta → retornar JSON al cliente
```

Si la sesión cae (Jasmin se reinicia, timeout de red, etc.), el sidecar intenta reconectar automáticamente con backoff exponencial: espera 1s, 2s, 4s, 8s, hasta un máximo de 30s entre intentos. Durante la reconexión, los requests de escritura reciben `503 Service Unavailable`. Los requests de lectura al health endpoint siguen respondiendo con estado `degraded`.

### Persist automático

Jasmin guarda su configuración en archivos en disco (`.jasmin/` en el directorio del usuario). Los cambios hechos vía jcli solo existen en memoria hasta que se ejecuta el comando `persist`. Si Jasmin se reinicia sin haber persistido, los cambios se pierden.

El sidecar ejecuta `persist` automáticamente después de cada operación de escritura exitosa. Si `persist` falla, la operación entera se considera fallida y se retorna error al cliente, aunque la operación sobre Jasmin haya tenido éxito. Esto garantiza consistencia entre el estado en memoria y el estado en disco.

### Proxy de envío

El sidecar no parsea ni valida el contenido de los mensajes. Recibe el request, lo convierte al formato de parámetros que espera la HTTP API de Jasmin, hace la llamada a `localhost:1401/send`, y retorna la respuesta. La autenticación del mensaje (usuario y contraseña Jasmin) viaja en el body y el sidecar las pasa a Jasmin tal cual — el sidecar no las verifica, Jasmin sí.

```
POST /sms/send  →  sidecar
    → validar X-API-Key del sidecar
    → construir query params para Jasmin: username, password, to, content, ...
    → GET/POST localhost:1401/send
    → Jasmin autentica al usuario Jasmin con username/password
    → Jasmin aplica sus propias reglas (throughput, balance, filtros de valor)
    → Jasmin retorna: Success "abc123" o Error "mensaje"
    → sidecar retorna: { "success": true, "data": { "message_id": "abc123" } }
```

Hay dos niveles de autenticación independientes:
1. **X-API-Key del sidecar**: verifica que el llamador tiene permiso de usar este sidecar.
2. **username/password del usuario Jasmin**: verifica que ese usuario puede enviar mensajes con las reglas que Jasmin tiene configuradas para él.

---

## Cómo encaja en el sistema UCaaS

El sidecar no conoce a UCaaS. Es agnóstico al sistema que lo llama. Desde su perspectiva, recibe requests HTTP autenticados y los ejecuta en Jasmin. Lo que hace UCaaS con eso es responsabilidad del orchestrator.

```
Cliente UCaaS
    │
    ▼
omnicanal-api
    │  (valida tenant, plan, rate limit UCaaS, balance UCaaS)
    ▼
sms-jasmin-orchestrator
    │  (routing: qué instancia Jasmin para esta org)
    │  (lee sms_infrastructure para obtener admin_api_url + admin_api_key)
    │
    ├─── Kafka/Redpanda (buffer de mensajes outbound)
    │         │
    │         ▼ (consumer rate-limited a 500 msg/seg)
    │    jasmin-admin-api  :8100
    │         │
    │         └─ POST /sms/send  →  Jasmin HTTP localhost:1401
    │
    └─── POST /admin/sync-user  →  jasmin-admin-api :8100
              │
              ├─ POST /users           →  jcli: user --add
              ├─ POST /smpp-connectors →  jcli: smppccm --add + start
              └─ POST /mt-routes       →  jcli: mtrouter --add
```

### Flujo de provisioning de un tenant nuevo

Cuando se activa SMS para una organización en UCaaS, el orchestrator:
1. Crea la DB `sms_tenant_{id}` y corre `sms_tenant.sql`
2. Llama a `POST /users` en el sidecar → crea el usuario Jasmin del tenant
3. Llama a `POST /smpp-connectors` → registra el conector SMPP del proveedor para ese tenant
4. Llama a `POST /smpp-connectors/{cid}/start` → activa el conector
5. Llama a `POST /mt-routes` → crea la ruta que asocia ese usuario con ese conector
6. Registra en `sms_infrastructure` los IDs de Jasmin asignados al tenant

El sidecar ejecuta cada paso en Jasmin y hace `persist` tras cada uno.

### Flujo de envío de un mensaje

1. `omnicanal-api` recibe el request de envío del cliente
2. El orchestrator escribe en `sms_tenant_{id}.messages` con `status='queued'`
3. Publica el mensaje en el topic Kafka de la instancia Jasmin
4. El consumer del orchestrator (rate-limited) toma el mensaje de Kafka
5. Llama a `POST /sms/send` en el sidecar con las credenciales del usuario Jasmin del tenant
6. El sidecar proxea a Jasmin HTTP `/send`
7. Jasmin aplica rutas y envía por SMPP al carrier
8. El orchestrator actualiza `status='submitted'` en la DB con el `jasmin_msgid` retornado
9. El DLR llega después desde el carrier → Jasmin notifica al webhook del orchestrator directamente

---

## Despliegue

### Por qué 1:1 con Jasmin

El sidecar necesita acceso a `localhost` del servidor donde vive Jasmin. No puede desplegarse en un servidor diferente porque el Telnet está en `localhost:8990` (no expuesto). Esto es intencional — es la garantía de seguridad.

### En VPS / cPanel

El sidecar corre como proceso adicional en el mismo servidor que Jasmin. El puerto 8100 debe ser accesible solo desde la red privada donde vive el orchestrator — nunca desde internet público.

### En k3s (Kubernetes / k3s)

Dos opciones:

**Opción A — Sidecar container en el mismo Pod:**
```yaml
spec:
  containers:
    - name: jasmin
      image: jasmin-sms-gateway:latest
    - name: jasmin-admin-api
      image: jasmin-admin-api:latest
      env:
        - name: JASMIN_TELNET_HOST
          value: "localhost"  # comparte red del Pod
```
Ventaja: no hay configuración de red — `localhost` funciona sin más.

**Opción B — Pod separado con ClusterIP:**
```yaml
# jasmin-admin-api en su propio Pod, Service tipo ClusterIP
# NetworkPolicy que solo permite tráfico desde el orchestrator
```
Ventaja: ciclo de vida independiente — se puede reiniciar el sidecar sin afectar Jasmin.

La Opción A es más simple para empezar. La Opción B es más limpia operacionalmente.

---

## Requisitos para funcionar

### Del servidor Jasmin

- Jasmin SMS Gateway instalado y corriendo
- Puerto Telnet accesible en `localhost:8990` (no necesita ser externo)
- Puerto HTTP API accesible en `localhost:1401` (no necesita ser externo)
- Usuario jcli con permisos de administración (default: `jcliadmin`)

### Del sidecar

Variables de entorno requeridas:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `JASMIN_TELNET_HOST` | Host del Telnet de Jasmin | `localhost` |
| `JASMIN_TELNET_PORT` | Puerto Telnet | `8990` |
| `JASMIN_TELNET_USER` | Usuario jcli | `jcliadmin` |
| `JASMIN_TELNET_PASSWORD` | Contraseña jcli | `jclipwd` |
| `JASMIN_HTTP_HOST` | Host de la HTTP API de Jasmin | `localhost` |
| `JASMIN_HTTP_PORT` | Puerto de la HTTP API | `1401` |
| `ADMIN_API_PORT` | Puerto de escucha del sidecar | `8100` |
| `ADMIN_API_KEY` | API Key que deben enviar los clientes | `sk-...` |

### De la infraestructura UCaaS

- La tabla `jasmin_instances` en `sms_infrastructure` debe tener `admin_api_url` y `admin_api_key` llenados para cada instancia Jasmin
- El orchestrator debe tener acceso de red al puerto 8100 del sidecar
- Firewall: el sidecar solo debe recibir tráfico del orchestrator (IP whitelist o NetworkPolicy)

---

## Limitantes conocidas

### Serialización de comandos Telnet

El jcli solo acepta un comando a la vez. Esto no es un problema para operaciones administrativas (agregar usuarios, crear rutas) que son poco frecuentes. Pero si múltiples workers del orchestrator intentan enviar mensajes por `/sms/send` simultáneamente, el proxy de envío también pasa por el mismo lock de sesión si usa Telnet.

**Aclaración importante:** `/sms/send` usa la HTTP API de Jasmin (`localhost:1401`), no Telnet. La HTTP API sí es concurrente — múltiples requests paralelos funcionan sin problema. El lock de sesión Telnet solo afecta a las operaciones administrativas (usuarios, rutas, filtros, etc.). El envío de mensajes en producción no tiene este bottleneck.

### Una sesión Telnet = un punto de falla de administración

Si la sesión Telnet cae y la reconexión falla (Jasmin no responde en Telnet), todas las operaciones administrativas quedan bloqueadas hasta que Jasmin responda. El envío de mensajes vía `/sms/send` sigue funcionando porque usa la HTTP API, que es independiente.

### filter --update no existe en jcli

Jasmin no implementa actualización de filtros. Modificar un filtro requiere eliminarlo y recrearlo. El sidecar implementa este patrón internamente en el endpoint `PATCH /filters/{fid}`: hace delete + add + persist. Si el delete tiene éxito pero el add falla, intenta restaurar el filtro original. Si la restauración también falla, el estado en Jasmin queda inconsistente — el filtro desaparece. El sidecar retorna error en este caso, pero las rutas/interceptores que referenciaban ese filtro pueden quedar rotas hasta que se recree manualmente.

### Persist es sincrónico y puede tardar

`persist` escribe todos los archivos de configuración a disco. En instancias con cientos de rutas, usuarios y filtros, puede tardar 1–2 segundos. Ese tiempo se suma a cada operación de escritura porque el sidecar espera que `persist` termine antes de retornar la respuesta. No hay forma de hacer `persist` asíncrono sin arriesgar pérdida de config si Jasmin se reinicia antes de que termine.

### Sin rollback de operaciones compuestas

Si el provisioning de un tenant requiere 4 operaciones en Jasmin (crear usuario, crear conector, activar conector, crear ruta) y la tercera falla, el sidecar no deshace las dos primeras. El orchestrator es responsable de detectar el error y ejecutar la limpieza o el reintento. El sidecar opera en modo "comando a comando" sin transacciones.

---

## Compatibilidad con otros sistemas

El sidecar no tiene ningún acoplamiento con UCaaS. Cualquier sistema que necesite administrar un Jasmin SMS Gateway puede usar este API:

- Un panel de administración web independiente
- Una herramienta CLI de operaciones
- Un script de onboarding de clientes
- Otro orchestrator de otra plataforma

El único requisito externo es:
1. Acceso de red al puerto del sidecar
2. La API Key configurada
3. Conocer los IDs de Jasmin que ya existen (cid de conectores, uid de usuarios, etc.) para operaciones de update/delete

No hay concepto de tenant, organización, plan o billing en el sidecar — esas abstracciones son del sistema que lo consume.

---

## Seguridad — resumen de decisiones

| Superficie | Decisión |
|---|---|
| Puerto Telnet de Jasmin (8990) | Nunca expuesto. Solo `localhost`. |
| Puerto HTTP API de Jasmin (1401) | Nunca expuesto. Solo `localhost`. |
| Puerto del sidecar (8100) | Expuesto solo en red privada. Nunca internet público. |
| Autenticación del sidecar | API Key en header `X-API-Key`. Obligatorio en todos los endpoints excepto `GET /health`. |
| Credenciales jcli | Solo en variables de entorno del sidecar. Nunca retornadas por el API ni loggeadas. |
| Contraseñas de usuarios Jasmin | Pasan en el body de `/sms/send` pero no se loggean. |
| API Key almacenada en DB | Cifrada con `encryption.py` en columna `jasmin_instances.admin_api_key`. |
| Logs | Registran método, path, status, duración. Nunca passwords ni keys. |

---

## Preguntas frecuentes

**¿Qué pasa si Jasmin se reinicia?**
La sesión Telnet cae. El sidecar detecta que el prompt no responde, marca el estado como `degraded` en `/health`, e inicia el ciclo de reconexión (1s, 2s, 4s... hasta 30s). En cuanto Jasmin vuelve a aceptar conexiones, el sidecar se reconecta y retoma el servicio. El envío de mensajes por `/sms/send` también falla durante el reinicio porque la HTTP API de Jasmin también cae, pero se recupera al mismo tiempo.

**¿Y si el sidecar se reinicia?**
Al arrancar, reconecta el Telnet y está listo. No pierde estado porque no tiene estado propio — Jasmin tiene la config.

**¿Puede haber múltiples sidecars para el mismo Jasmin?**
No. Dos sidecars intentando mantener sesiones Telnet simultáneas con el mismo Jasmin causarían conflictos de `persist` y condiciones de carrera en las operaciones. La relación es estrictamente 1:1.

**¿Qué versiones de Jasmin soporta?**
El sidecar depende del comportamiento del jcli y la HTTP API de Jasmin. Ha sido diseñado para Jasmin 0.10.x. Las versiones anteriores pueden no soportar todos los parámetros (ej: `smpps_cred` fue agregado en versiones recientes). Verificar la versión instalada antes de usar funcionalidades avanzadas como interceptors o EvalPyFilter.

**¿El sidecar puede convivir con acceso manual vía Telnet?**
Sí, pero no es recomendable en producción. Si un operador hace cambios manuales vía Telnet mientras el sidecar está activo, el sidecar no se entera. La DB del orchestrator (`sms_infrastructure`) puede quedar desincronizada con el estado real de Jasmin. Para diagnósticos o emergencias está bien. Para cambios regulares, usar siempre el API del sidecar.
