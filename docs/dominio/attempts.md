# `attempts`: admisión, ejecución y resultado de un intento

Estado: implementado. Es el puente entre la API de participación, el runtime, la víctima, los oráculos y el ciclo de defensa. Un intento conserva la identidad, la ruta y la versión que el servidor fijó al admitirlo.

## Entradas al código

| Archivo | Responsabilidad |
| --- | --- |
| [schemas.py](../../backend/src/agent_zero/attempts/schemas.py) | `AttemptCreate` cerrado y sus formas de mensaje. |
| [models.py](../../backend/src/agent_zero/attempts/models.py) | Tabla `attempts`, estados y resultados separados. |
| [attempt_submission_service.py](../../backend/src/agent_zero/attempts/attempt_submission_service.py) | Autorización de campaña, límites, ruta, versión, run y outbox transaccional. |
| [attempt_execution_handler.py](../../backend/src/agent_zero/attempts/attempt_execution_handler.py) | Handler durable `arena_attempt`: checkpoints, conversación y evaluación. |
| [attempt_worker.py](../../backend/src/agent_zero/attempts/attempt_worker.py) | Recupera fallos, procesa violaciones y ejecuta el planificador de defensa. |
| [attempt_query_service.py](../../backend/src/agent_zero/attempts/attempt_query_service.py) | `CallContext`, historial, drenaje y proyección pública/de operación. |
| [router.py](../../backend/src/agent_zero/attempts/router.py) | Envío y lectura con `CurrentSession`. |

El [runtime](runtime.md) ejecuta los pasos; [events](events.md) publica la evidencia; [oracles](oracles.md) determina el resultado. No hay un consumidor independiente de comandos que decida el veredicto con un LLM.

## Contratos y datos

`POST /api/attempts` requiere Bearer del participante y devuelve 202. Ejemplos alternativos:

```json
{"message":"Consulta el pedido A-1001.","idempotency_key":"consulta-1"}
```

```json
{"messages":["Consulta A-1001.","¿Y su estado?"],"objective_id":"OBJ-ORDER","idempotency_key":"consulta-2"}
```

Debe enviarse exactamente `message` o `messages`: de uno a cuatro turnos, cada uno de 1–4000 caracteres y no sólo espacios. El objetivo es opcional y debe ser uno de los tres conocidos. No se aceptan cliente, ruta, versión, origen ni fixtures desde esta API.

### Conversación del chat (`continues`)

`continues` es opcional: el id de un intento anterior de la misma sesión cuya conversación continúa este. Lo usa el chat del participante. Reglas ([conversation.py](../../backend/src/agent_zero/attempts/conversation.py)):

- **Validación:** el intento anterior debe existir en la misma sesión (si no, 404) y estar terminado (si no, 409). Una conversación admite como máximo `MAX_PREVIOUS` = 6 intentos; el siguiente devuelve 409 y el cliente abre otra.
- **Historial armado por el servidor:** sale de sus filas; el cliente sólo dice a qué intento responde, así que no puede inventar respuestas del asistente. Las respuestas previas van con los canarios redactados (`[referencia]`), igual que las vio el participante.
- **Ejecución:** `ConversationExecutor.start` antepone los turnos previos como texto: los mensajes del participante con rol `user` y las respuestas con rol `assistant`. Las herramientas de esos turnos no se repiten. La procedencia sólo cuenta lo que escribió el participante, nunca la respuesta previa del asistente.
- **Almacenamiento:** el enlace se guarda en la tabla `attempt_links` (`attempt_id`, `previous_attempt_id`). Es una tabla nueva, así que `create_all` la crea sin migración; forma parte de `ROUND_TABLES`.
- **Idempotencia:** la comparación incluye `continues`. Repetir la clave con otro `continues` devuelve 409.
- **Vistas:** el historial y el detalle devuelven `continues`.

`GET /api/attempts` devuelve el historial propio; `GET /api/attempts/{id}` devuelve 404 para un intento ajeno o inexistente. Operación usa sus rutas separadas en [arena/operator_router.py](../../backend/src/agent_zero/arena/operator_router.py).

La fila guarda `session_id`, `origin`, `campaign_id`, `customer_id`, `policy_version`, `route`, `run_id`, clave, mensajes, estado, resultado, respuesta, `assessment`, fechas y `defense_processed`. Tiene unicidad por `(session_id, idempotency_key)` y por `run_id`; no tiene una columna `case_id`.

| Campo | Valores |
| --- | --- |
| `status` | `queued`, `running`, `evaluated`, `inconclusive`. |
| `outcome` | Nulo hasta terminar; después `confirmed_violation`, `prevented`, `not_achieved`, `contained_honeypot` o `inconclusive`. |
| `origin` | `audience` o `autonomous`, fijado por el servidor. |

## Admisión e idempotencia

1. Reservar el escritor SQLite con `BEGIN IMMEDIATE`, además del lock local.
2. Resolver primero la clave idempotente. Si mensajes, objetivo, origen y campaña coinciden, devolver la fila existente; si difieren, 409.
3. Para campaña, exigir que siga `running` y que el origen sea autónomo. Resolver la sesión y exigir entradas abiertas.
4. Aplicar límite de cola por origen, cola por sesión y frecuencia. Los excesos devuelven 429 con `Retry-After` en segundos enteros: por frecuencia, lo que falta para que salga de la ventana de un minuto el intento que deja a la sesión bajo el límite (mínimo 1); con la cola llena, 5 s fijos, porque se libera cuando termina un intento pendiente y no hay una hora conocida.
5. Pedir la ruta, leer la versión activa y crear intento, run y eventos en una sola transacción.
6. Después de commit, despachar el outbox. Un fallo de publicación no convierte la admisión en una segunda operación.

Defaults de [Settings](../../backend/src/agent_zero/config.py): cola 40 por origen, una ejecución pendiente por sesión y 12 intentos/minuto/sesión. Audiencia y autonomía tienen contadores de cola separados; no son prioridades de CPU independientes.

## Ejecución y recuperación

El handler fija `running` y `attempt_started`, prepara la conversación y avanza un checkpoint por paso. El checkpoint guarda las herramientas propuestas antes de ejecutarlas. [Victim](victim.md) identifica cada operación y persiste su resultado para que una recuperación no duplique reembolsos o memoria.

Al terminar, guarda respuesta, `Assessment` y `attempt_evaluated` juntos. El trabajador transforma runs `failed`/`cancelled` en intentos inconclusos, conserva la razón y emite el evento. Procesa las violaciones pendientes con `FindingService` y sólo después marca `defense_processed`; esa marca permite a campañas esperar a que se procese su último hallazgo.

Los mensajes se guardan en JSON tal como fueron admitidos; esa columna no usa el cifrado del Memory Bank. Por ello la redacción de eventos no equivale a redacción integral del historial.

La respuesta pública sustituye canarios por `[referencia]` y omite identidad interna, ruta, run y evaluación. Antes de revelar, una violación protegida y una contención se muestran como `apparent_success`. Tras revelar, el dueño puede leer el resultado real; las trazas siguen reservadas a Operación.

## Pruebas y comandos

```bash
cd backend
uv run pytest tests/arena/test_core_cycle.py tests/arena/test_admission_and_campaign.py tests/arena/test_recovery.py tests/arena/test_control_concurrency.py tests/arena/test_transactional_events.py tests/arena/test_tool_retries.py tests/arena/test_attempt_limits.py tests/arena/test_pause_in_flight.py tests/arena/test_operator_authorization.py tests/arena/test_sticky_honeypot_route.py -q
```

| Cobertura | Archivo de prueba |
| --- | --- |
| Ciclo útil → violación → parche → repetición y proyección pública | [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py). |
| Frecuencia/cupo, pausa y versión fijada al admitir | [test_admission_and_campaign.py](../../backend/tests/arena/test_admission_and_campaign.py). |
| Largo máximo del mensaje (4000 sí, 4001 no), 429 por intento pendiente, por cola llena y por frecuencia con reloj inyectado, y `Retry-After` de cada uno | [test_attempt_limits.py](../../backend/tests/arena/test_attempt_limits.py). |
| Pausa con un intento en ejecución: termina evaluado, conserva sus eventos y los envíos nuevos reciben 409 | [test_pause_in_flight.py](../../backend/tests/arena/test_pause_in_flight.py). |
| Un token de participante válido recibe 401 en las rutas de operación y no cambia el estado | [test_operator_authorization.py](../../backend/tests/arena/test_operator_authorization.py). |
| Solicitudes simultáneas con una clave; conflicto de payload; carreras con activación/reversión | [test_control_concurrency.py](../../backend/tests/arena/test_control_concurrency.py). |
| Fallo antes de commit, caída después de commit y recuperación del evento | [test_transactional_events.py](../../backend/tests/arena/test_transactional_events.py). |
| App recreada y resultado de herramienta reutilizado | [test_recovery.py](../../backend/tests/arena/test_recovery.py), [test_tool_retries.py](../../backend/tests/arena/test_tool_retries.py). |
| Campos extra `route` o `environment` en el envío: 422 sin crear intento ni consumir la clave de idempotencia | [test_sticky_honeypot_route.py](../../backend/tests/arena/test_sticky_honeypot_route.py). |

Son pruebas automatizadas de la suite backend verificada, con proveedor simulado. El [protocolo central](../pruebas/README.md) describe la ejecución completa y la comprobación LIVE independiente.

## Continuar este dominio

Para añadir un estado o resultado, actualizar modelos, proyecciones públicas, arena, frontend, métricas y recuperación en la misma entrega. No inferir que `evaluated` significa éxito defensivo.

Para cambiar la cola, mantener la reserva SQLite y la fijación de política dentro de la transacción. La clave del runtime por sí sola no compara payloads: el contrato 409 pertenece a esta admisión. Una cancelación o error después de un efecto no lo deshace; conservar `operation_id` y el registro persistido de la herramienta.
