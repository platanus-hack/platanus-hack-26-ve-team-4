# Events: log durable, outbox y SSE

Estado: implementación revisada sobre la base funcional `1d0e21d`. Los eventos sirven para reconstruir evidencia y actualizar lectores. Los workers del producto consultan estado persistido; este módulo no es un bus externo de comandos ni un supervisor LLM.

## Componentes y tablas

| Archivo | Función |
| --- | --- |
| [models.py](../../backend/src/agent_zero/events/models.py) | `EventType`, visibilidad y tablas de eventos/entregas. |
| [event_store.py](../../backend/src/agent_zero/events/event_store.py) | Staging transaccional, redacción, consulta privada e historia pública. |
| [event_delivery.py](../../backend/src/agent_zero/events/event_delivery.py) | Publica eventos confirmados y registra auditoría con deduplicación por ID/hash. |
| [broker.py](../../backend/src/agent_zero/events/broker.py) | Caché local y notificaciones para despertar lectores. |
| [sse.py](../../backend/src/agent_zero/events/sse.py) | Cursor, consulta periódica al log y formato SSE. |
| [public_projection.py](../../backend/src/agent_zero/events/public_projection.py) | Lista cerrada de campos públicos. |
| [router.py](../../backend/src/agent_zero/events/router.py) | `GET /api/arena/events`. |

`product_events` tiene ID entero monotónico, tipo, visibilidad, referencias opcionales de intento/sesión/política, timestamp, JSON y una `dedup_key` única opcional. `product_event_delivery` añade una fila por evento con `delivered_at` inicialmente vacío.

Los tipos actuales son `round_started`, `attempt_queued`, `attempt_started`, `attempt_completed`, `tool_proposed`, `tool_denied`, `tool_completed`, `tool_failed`, `route_changed`, `attempt_evaluated`, `finding_opened`, `patch_proposed`, `patch_validated`, `policy_activated`, `policy_rolled_back` y `probe_round_closed`. Este último es público, lo emite el planificador adaptive al cerrar la ronda de una versión (no confundir con `round_started`, que es la ronda de arena) y solo proyecta `probe_round`, `queries`, `violations` y `mutator`. Un tipo nuevo exige revisar emisor, visibilidad, proyección y lectores.

## Publicar junto con el cambio de dominio

El llamador reserva el escritor antes de leer y llama `EventStore.stage(db, draft, dedup_key=...)` dentro de la misma transacción de su cambio. El servicio inserta evento y entrega pendiente, pero no hace commit ni publica. Así, un rollback elimina el estado y su evento juntos.

Después del commit se llama `dispatch_pending()`. `emit()` ofrece esa secuencia para eventos autónomos; no debe usarse para separar en dos commits un cambio de dominio que exige su evento.

El dispatcher reserva el escritor, toma hasta 100 pendientes ordenados y calcula el hash del `TraceEvent`. Busca en auditoría la pareja `(event_id, event_hash)`: si una caída sucedió después del append pero antes del acknowledgment, evita añadir otra entrada firmada. Publica el mismo ID al broker, marca la entrega y confirma.

Una publicación puede repetirse tras una caída; los IDs estables permiten deduplicarla. No asumir entrega exactamente una vez a cualquier consumidor. La recuperación de eventos confirmados no depende de que sobreviva la memoria del proceso.

## Lectura pública y reconexión

La ruta SSE acepta `Last-Event-ID`, responde `text/event-stream`, desactiva el buffer de nginx y envía comentarios heartbeat cada 15 s. El formato conserva `id`, nombre de evento y JSON del `TraceEvent`.

Sin cursor, la conexión sigue eventos nuevos desde el ID actual del broker. Con cursor, recupera los posteriores. La fuente de historia es SQLite; la caché del broker conserva por defecto sólo 500 eventos y las colas de suscripción están acotadas a 1000 elementos.

`public_stream` consulta el log al despertar y, como máximo, después de un segundo sin notificación local. Esto permite ver eventos producidos por otro proceso y evita saltar un ID público anterior por recibir primero una notificación local de ID mayor. El cursor se mantiene sobre el log ordenado.

La historia pública se limita desde `RoundMetadata.first_event_id`; un reset conserva IDs crecientes y abre un rango nuevo. El navegador detecta actualmente el cambio de ronda mediante polling del estado, aunque el backend también emite `round_started`.

## Privacidad e invariantes

- Sólo se envían eventos `visibility=public` al stream público.
- La proyección anula `attempt_id` y `session_id`; sólo conserva en `data`: `status`, `outcome`, `finding_id`, `objective_id`, `version`, `passed` y `round_id`.
- Ruta, argumentos, salidas, canarios y detalles de oráculos quedan en eventos de operación, consultados por el endpoint autorizado de evidencia.
- El store redacta PII recursivamente antes de persistir. La redacción de un número no rompe la serialización JSON.
- La clave de deduplicación identifica una transición concreta; no debe reutilizarse para dos contenidos distintos.
- El broker local es una señal para despertar, no la autoridad de puntuación ni de evidencia.

La firma y recuperación del archivo de auditoría pertenecen a [telemetría](./telemetry.md). Una nueva salida pública debe agregarse a la lista permitida sólo después de revisar qué información revela durante la fase provisional.

## Pruebas concretas

Desde la raíz:

```bash
cd backend
uv run pytest tests/events tests/arena/test_transactional_events.py \
  tests/arena/test_recovery.py tests/arena/test_tool_retries.py -q
```

| Archivo | Evidencia comprobada |
| --- | --- |
| [test_broker.py](../../backend/tests/events/test_broker.py) | IDs, suscripción, cierre y reanudación sólo de eventos faltantes. |
| [test_sse.py](../../backend/tests/events/test_sse.py) | Formato y exclusión de eventos privados. |
| [test_transactional_events.py](../../backend/tests/arena/test_transactional_events.py) | Rollback cola/outbox, caída antes de publicar, caída tras auditoría, dispatchers concurrentes y eventos remotos sin notificación local. |
| [test_recovery.py](../../backend/tests/arena/test_recovery.py) | Historia recuperable después del reinicio y de expulsar la caché local. |

El proxy SSE también formó parte del smoke Docker previo. Ver [evidencias](../pruebas/evidencias.md) y [frontend](./frontend.md).

## Límites y extensión

La consulta de pendientes y la auditoría se realizan bajo reserva de escritor SQLite. Esto simplifica consistencia y puede limitar el rendimiento cuando crezca la historia. No se ha medido una capacidad distribuida de producción.

Si se añade otro consumidor o se mueve el log a otra base, conservar el staging en la transacción del dominio, el cursor durable, los IDs estables y la separación de visibilidades. Una UI que necesite historia completa debe consultarla por un contrato explícito: la lista de actividad actual muestra sólo la conexión reciente.
