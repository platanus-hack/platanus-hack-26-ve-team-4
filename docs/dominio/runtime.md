# Runtime: pasos durables y ejecución concurrente

Estado: implementación revisada sobre la base funcional `1d0e21d`. El runtime ejecuta handlers registrados y conserva sus checkpoints. La política de negocio se decide en [policies](./policies.md) y el acceso a herramientas pasa por el gateway de la flota.

## Archivos y modelo

| Archivo | Responsabilidad |
| --- | --- |
| [handlers.py](../../backend/src/agent_zero/runtime/handlers.py) y [step_results.py](../../backend/src/agent_zero/runtime/step_results.py) | Contrato `StepContext` y resultados tipados de un paso. |
| [run_enqueue_service.py](../../backend/src/agent_zero/runtime/run_enqueue_service.py) | Crea run más evento de cola; permite participar en una transacción del llamador. |
| [run_worker.py](../../backend/src/agent_zero/runtime/run_worker.py) | Selecciona lotes listos con concurrencia acotada y sondeo. |
| [run_lease.py](../../backend/src/agent_zero/runtime/run_lease.py) | Reserva durable, heartbeat y liberación condicionada al propietario. |
| [step_runner.py](../../backend/src/agent_zero/runtime/step_runner.py) | Revalida admisión, ejecuta el handler y confirma el resultado con fencing. |
| [step_transitions.py](../../backend/src/agent_zero/runtime/step_transitions.py) | Aplica estados, incrementa pasos y limita reintentos. |
| [models.py](../../backend/src/agent_zero/runtime/models.py) | Tablas `runs`, `run_events` y `run_leases`. |

`Run` fija agente/versión, handler, input, clave idempotente, estado, índice de paso, checkpoint, salida, motivo de fallo y `trace_id`. Las fechas vuelven como UTC consciente mediante `UtcDateTime`.

```text
queued → running → queued       Advance(checkpoint)
                 → waiting     Wait(until, checkpoint)
                 → succeeded   Complete(output)
                 → failed      Fail(reason) o error definitivo
queued/running/waiting → cancelled
```

`StepContext` contiene identidad recién admitida, reloj, input/checkpoint e interfaz `ToolAccess`; el handler no recibe directamente el registro de herramientas. Un `Advance` o `Wait` exitoso incrementa `step_index` y reinicia el contador de intentos. Un fallo definitivo conserva el índice del paso que falló.

## Cola, leases y recuperación

La configuración inicial es `runtime_worker_concurrency=2`, sondeo de 0,5 s y máximo de tres intentos por paso. El worker procesa un lote con `gather` y espera su final antes del siguiente; no mantiene una cola externa ni un ejecutor ilimitado.

El claim usa `BEGIN IMMEDIATE`. Si el run no es terminal, está listo y no tiene lease vigente, asigna un propietario nuevo y marca `running`. El lease dura 30 s y se renueva cada tercio de ese plazo mientras el paso continúa. Los handlers del producto no se reclaman durante un reset de ronda.

Al confirmar, `_finish` exige que el propietario siga siendo el mismo. Un worker desplazado por una recuperación no puede sobrescribir el checkpoint ni borrar el lease del propietario nuevo. Después de una caída dura se puede reclamar el run al vencer la reserva; el último checkpoint confirmado sigue siendo la entrada del paso.

Esto protege la confirmación del runtime. Los efectos externos necesitan su propia idempotencia: [victim](./victim.md) conserva operaciones y resultados antes de responder. No se obtiene ejecución exactamente una vez de cualquier servicio externo sólo por usar leases.

## Reintentos, cancelación e idempotencia

- Errores reconocidos como transitorios y `ModelLimitReachedError` vuelven a `queued` hasta el tope; los demás terminan `failed`. El texto persistido se redacta y limita.
- Los reintentos del runtime son inmediatos; el backoff de llamadas al modelo pertenece a `RetryingModel`.
- Antes de cada paso se repite admisión. Una versión deprecada o revocada no obtiene otra ejecución válida; el gateway también verifica identidad por llamada.
- Cancelar marca el run, elimina la espera e impide confirmar un resultado que llegue después. No interrumpe físicamente toda herramienta ya iniciada ni deshace efectos confirmados.
- La clave de `Run.idempotency_key` es única globalmente. `RunEnqueueService` devuelve el run existente sin comparar el input. La garantía de conflicto 409 por payload distinto pertenece a [attempts](./attempts.md), que aplica su propio contrato.

## API y extensión de handlers

`POST /api/runtime/runs` devuelve 202 con `run_id`; `GET /api/runtime/runs/{id}` devuelve su estado; `POST /api/runtime/runs/{id}/cancel` cancela. La aplicación monta estas rutas con autorización de operador. Un handler desconocido se rechaza al encolar; un agente no admitido falla al ejecutar.

Para agregar un handler: definir input cerrado, registrar su nombre al iniciar la aplicación, publicar/aprobar el manifiesto correspondiente y devolver un `StepResult` serializable. Conservar checkpoints pequeños, operaciones repetibles y la versión del agente fija. Usar `context.tools` para herramientas y comprobar recuperación en mitad del flujo.

## Pruebas ejecutables

Desde la raíz:

```bash
cd backend
uv run pytest tests/runtime -q
uv run pytest tests/runtime/test_run_leases.py tests/arena/test_recovery.py \
  tests/arena/test_tool_retries.py -q
```

| Archivo de pruebas | Casos relevantes |
| --- | --- |
| [test_run_leases.py](../../backend/tests/runtime/test_run_leases.py) | Dos workers ante el mismo checkpoint, reserva vencida con resultado antiguo y renovación durante proveedor lento. |
| [test_run_worker.py](../../backend/tests/runtime/test_run_worker.py) | Espera/reinicio, run huérfano, fallos transitorios, cancelación, límite de concurrencia y nueva admisión por paso. |
| [test_step_runner.py](../../backend/tests/runtime/test_step_runner.py) | Handler ausente, acceso ligado al principal, continuidad de traza y redacción de fallos/reintentos. |
| [test_run_enqueue_service.py](../../backend/tests/runtime/test_run_enqueue_service.py) | Alta inmediata, clave repetida y runs distintos sin clave. |
| [test_tool_retries.py](../../backend/tests/arena/test_tool_retries.py) | El reintento de una operación de reembolso no repite su efecto. |

La suite previa de backend aprobó 860 pruebas con dos LIVE opcionales omitidas y sin advertencias. La reproducción de esta evidencia se organiza en [pruebas](../pruebas/README.md).

## Límites para el siguiente cambio

`runtime` importa actualmente el estado de reset de `arena`; la dependencia no es todavía una abstracción genérica de mantenimiento. Separarla exige conservar las pruebas de exclusión durante reset. La parada normal espera los pasos activos, de modo que su duración depende de los límites de las herramientas/proveedor. Añadir un plazo de parada o backoff exige pruebas de cancelación, reservas y efectos confirmados, no sólo un cambio de temporizador.
