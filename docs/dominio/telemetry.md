# Telemetry: trazas y auditoría recuperable

Estado: implementado. Las trazas explican ejecución y latencia; la auditoría firma decisiones y eventos. Sus almacenes y garantías son diferentes del outbox de [events](./events.md).

## Archivos de referencia

| Código | Responsabilidad |
| --- | --- |
| [otel_setup.py](../../backend/src/agent_zero/telemetry/otel_setup.py), [spans.py](../../backend/src/agent_zero/telemetry/spans.py) | Proveedor de trazas, exportadores y atributos saneados. |
| [audit_log.py](../../backend/src/agent_zero/telemetry/audit_log.py) | Verificación y publicación de una entrada firmada bajo locks. |
| [audit_schemas.py](../../backend/src/agent_zero/telemetry/audit_schemas.py) | Evento, entrada, decisión y reporte de verificación. |
| [audit_hashing.py](../../backend/src/agent_zero/telemetry/audit_hashing.py), [audit_verifier.py](../../backend/src/agent_zero/telemetry/audit_verifier.py) | Firma y comprobación de la cadena. |
| [audit_store.py](../../backend/src/agent_zero/telemetry/audit_store.py), [audit_files.py](../../backend/src/agent_zero/telemetry/audit_files.py) | Bloqueo de archivo, append con fsync y escritura atómica. |
| [audit_anchor.py](../../backend/src/agent_zero/telemetry/audit_anchor.py), [audit_journal.py](../../backend/src/agent_zero/telemetry/audit_journal.py) | Ancla firmada y recuperación de un append interrumpido. |

## Trazas

`AGENT_ZERO_OTEL_EXPORTER` admite `none`, `memory`, `console` y `otlp`. `otlp` exige `AGENT_ZERO_OTEL_ENDPOINT`; `memory` habilita la consulta local por run en `/api/fleet/runs/{run_id}/trace`, con autorización de operador. Otro exportador no proporciona esa consulta en memoria y el endpoint responde 409.

La flota conecta spans del runtime, gateway y los cinco modelos de `LlmGateway`. Los identificadores `trace_id` y `span_id` correlacionan la decisión con el run. Construir modelos por fuera de ese gateway puede perder la instrumentación. No añadir mensajes, secretos ni razonamiento interno como atributos de spans.

## Auditoría y recuperación

Dentro de `AGENT_ZERO_DATA_DIR/audit/` se guardan:

| Archivo | Propósito |
| --- | --- |
| `audit.jsonl` | Entradas ordenadas con predecesor, firma, actor, decisión y trazas. |
| `audit.jsonl.anchor` | Número de entradas y último hash con firma. |
| `audit.jsonl.pending` | Entrada firmada pendiente durante un append; puede quedar tras una caída. |
| `audit.jsonl.lock` | Lock del sistema operativo para coordinar procesos. |

El append toma el lock, recupera una operación pendiente válida, verifica la historia, prepara el journal, escribe y sincroniza la línea, publica el ancla y limpia el journal. La clave HMAC se deriva de `identity_signing_key` y no se almacena en esos archivos.

Una caída entre línea y ancla puede recuperarse si el journal demuestra exactamente el append esperado. Una historia alterada, un tail ajeno o una entrada pendiente falsificada siguen siendo errores de integridad. No arreglar un incidente borrando el ancla o generando una nueva sobre un archivo desconocido.

El outbox usa IDs durables para reconstruir entregas después de un commit; el bloqueo del archivo protege la cadena también frente a otros escritores de auditoría del gateway. El protocolo no ofrece una transacción distribuida entre JSONL y SQLite.

## Pruebas

```bash
cd backend
uv run pytest tests/telemetry tests/arena/test_transactional_events.py -q
uv run pytest tests/fleet/test_fleet_scenario.py tests/runtime/test_run_tracing.py tests/llm/test_traced_model.py -q
```

| Archivo | Evidencia cubierta |
| --- | --- |
| [test_audit_durability.py](../../backend/tests/telemetry/test_audit_durability.py) | Cinco procesos y 75 appends; fallos antes/después de la línea y recuperación de tail parcial. |
| [test_audit_anchor.py](../../backend/tests/telemetry/test_audit_anchor.py), [test_audit_verifier.py](../../backend/tests/telemetry/test_audit_verifier.py) | Ancla, truncamiento, firmas y alteración. |
| [test_transactional_events.py](../../backend/tests/arena/test_transactional_events.py) | Caídas entre estado, audit y publicación; dispatchers concurrentes. |
| [test_spans.py](../../backend/tests/telemetry/test_spans.py), [test_otel_setup.py](../../backend/tests/telemetry/test_otel_setup.py) | Redacción, contexto y configuración de exportadores. |

El [recorrido de flota](../prueba-flota.md) comprueba por HTTP trazas y auditoría. El ensayo guardado pasó 22/22 controles; es diferente de una prueba de capacidad del colector o del disco.

## Límites y continuidad

El log completo se relee al verificar y añadir entradas. `flock` presupone un sistema compatible con POSIX; no hay implementación nativa para Windows. El ancla sigue en el mismo host: quien tenga la clave puede reconstruir firmas, y borrar log y ancla juntos no demuestra que antes hubo historia.

Próximas mejoras: anclaje externo, retención/exportación y medición de coste por append a medida que crece el archivo. Respaldar log, ancla y journal como conjunto, además de las claves correspondientes. El borrado de datos personales y la retención de auditoría necesitan un protocolo propio antes de utilizar datos fuera del laboratorio.
