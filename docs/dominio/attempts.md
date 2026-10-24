# `attempts`: intentos y cola

Categoría: arena · Responsable: Francisco · Issues: #6

## Propósito

Recibe cada intento, sea de una persona o del Prober, lo encola contra la víctima o el señuelo con la versión de política vigente y guarda su estado y su resultado.

## Estado hoy

| Archivo | Contenido |
| --- | --- |
| `models.py` | Tabla `attempts` (clave de idempotencia única por sesión) y los enums `AttemptStatus`, `AttemptOutcome` y `AttemptOrigin`. |
| `schemas.py` | `AttemptCreate` (`message` o `messages`, de 1 a 4 turnos de hasta 4000 caracteres), `AttemptPublicView` y `AttemptOperatorView`. |
| `execution.py` | `ArenaWiring`: el punto de conexión con la víctima, los oráculos y la versión de política. |
| `attempt_submission_service.py` | Idempotencia, límites, versión fijada y encolado del run. |
| `rate_limits.py` | Un intento cada `AGENT_ZERO_ATTEMPT_MIN_INTERVAL_SECONDS` (3) por sesión: 429. Cola global de `AGENT_ZERO_ATTEMPT_QUEUE_LIMIT` (20) intentos abiertos: 503. Ambos con `Retry-After`. |
| `attempt_tracker.py` | Proceso en segundo plano que sigue el run de cada intento abierto y lo pasa a `running`, `evaluated` o `inconclusive`. |
| `attempt_events.py` | Publica `attempt_queued`, `attempt_started` y `attempt_evaluated` dos veces: completa para operación y sin identificadores para el público. |
| `router.py` | `POST /api/attempts` (202 nuevo, 200 si la clave ya existía), `GET /api/attempts` (los de la sesión, del más reciente al más antiguo) y `GET /api/attempts/{id}`, solo para la sesión dueña. |
| `arena_state.py`, `arena_router.py` | `GET /api/arena/state`, público: contadores de la ronda para la pantalla proyectada. Suma violaciones confirmadas y éxitos en el señuelo en `apparent_successes` hasta la revelación; `findings_open` es `null` mientras no exista el registro de hallazgos. |
| `operator_router.py` | `GET /api/operator/attempts` y `GET /api/operator/attempts/{id}`, con ruta, run y resultado reales. |

### Conexión con otros dominios

Hasta que existan la víctima de la arena (#5), los oráculos (#8) y el registro de políticas (#11), el intento se conecta por `app.state.arena` (`ArenaWiring`):

- **`target`** (`ArenaTarget`): agente aprobado y handler del runtime, `arena_attempt` por defecto. El handler recibe `attempt_id`, `session_id`, `customer_id`, `messages`, `objective_id`, `policy_version` y `route`; si su salida trae `reply`, es lo que ve el participante. Sin `target`, `POST /api/attempts` responde 503.
- **`evaluator`** (`AttemptEvaluator`): recibe el intento y la salida del run y devuelve un `AttemptOutcome`. Sin evaluador, un intento terminado queda `inconclusive`: no se inventa un veredicto.
- **`policy_version`**: función que devuelve la versión activa al encolar; hoy devuelve 0.

Un run que falla o se cancela deja el intento `inconclusive` sin consultar al evaluador. El resultado público convierte `confirmed_violation` y `contained_honeypot` en `apparent_success` hasta la revelación (#13). Siguen pendientes la fase de la ronda (409 con entradas cerradas, #15), el cupo propio del Prober y la ruta decidida por `routing` (hoy se copia la de la sesión).

## Responsabilidades

1. `POST /api/attempts` con token de sesión, mensaje, objetivo opcional y clave de idempotencia.
2. Validar tamaño, frecuencia por sesión, cupo global y fase de la ronda.
3. Pedir la ruta a `routing` y fijar la versión de política activa.
4. Encolar un run del runtime con el handler de la víctima o del señuelo y el contexto de la sesión.
5. Pasar a `evaluated` o `inconclusive` cuando los oráculos devuelven su veredicto.
6. Exponer `GET /api/attempts/{id}` con la proyección permitida para cada vista.

## Contratos

| Contrato | Campos |
| --- | --- |
| `AttemptCreate` | `message` o `messages` (hasta 4), `objective_id` opcional, `idempotency_key`. |
| `Attempt` | `id`, `session_id`, `origin` (`audience` o `autonomous`), `case_id` opcional, `policy_version`, `route`, `run_id`, `status`, `outcome`, fechas. |
| `AttemptPublicView` | Estado y resultado provisional; nunca ruta, canarios ni eventos de operación. |

## Eventos

- **Produce:** `attempt_queued`, `attempt_started`.
- **Consume:** `attempt_evaluated` de `oracles` para cerrar el intento.

## Reglas

- La misma clave de idempotencia devuelve el mismo intento y no encola otro run.
- Un intento conserva su `policy_version` de principio a fin.
- Con entradas cerradas, el intento se rechaza con 409.
- El Prober tiene cupo propio para no desplazar a la audiencia.

## Uso de la flota

- `runtime` ejecuta el intento como run, con reintentos y estado durable.
- `telemetry` agrupa todo el intento en una sola traza.

## Estructura prevista

| Archivo | Responsabilidad |
| --- | --- |
| `models.py` | Tabla `attempts` además de los enums. |
| `repository.py` | Persistencia e idempotencia. |
| `attempt_submission_service.py` | Validación, ruta, versión y encolado. |
| `attempt_query_service.py` | Proyecciones por vista. |
| `rate_limits.py` | Cupos por sesión y global. |
| `router.py` | `POST` y `GET`. |

## Pruebas de éxito

- Dos envíos con la misma clave crean un solo intento y un solo run.
- Un intento encolado antes de una activación conserva la versión anterior.
- La vista pública de un intento desviado no revela la ruta.
