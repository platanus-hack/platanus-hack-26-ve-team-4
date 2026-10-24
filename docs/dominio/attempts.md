# `attempts`: intentos y cola

Categoría: arena · Responsable: Francisco · Issues: #6

## Propósito

Recibe cada intento, sea de una persona o del Prober, lo encola contra la víctima o el señuelo con la versión de política vigente y guarda su estado y su resultado.

## Estado hoy

| Archivo | Contenido |
| --- | --- |
| `models.py` | `AttemptStatus`: `queued`, `running`, `evaluated`, `inconclusive`. `AttemptOutcome`: `confirmed_violation`, `prevented`, `not_achieved`, `contained_honeypot`, `inconclusive`. |

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
