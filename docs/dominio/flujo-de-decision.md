# Flujo de decisión implementado

El núcleo combina servicios deterministas, runs durables y eventos de evidencia. No hay un supervisor LLM con autoridad sobre ruta, permisos, veredictos o activación. Las instrucciones de una conversación no deciden esas transiciones.

## Secuencia real

1. `AttemptSubmissionService` valida sesión, ronda y cupos bajo reserva de escritura. Resuelve la ruta y fija la versión de política.
2. Guarda intento, run y eventos de admisión en la misma transacción de `app.db`.
3. `RunWorker` obtiene un lease y ejecuta `AttemptExecutionHandler` desde su checkpoint.
4. `ConversationExecutor` alterna generación, ejecución de herramientas y fin de turno. Persiste la propuesta antes de efectos; cada llamada pasa por el gateway con contexto del servidor.
5. El handler obtiene un `Assessment` de los oráculos y persiste resultado y evento evaluado. Un fallo de infraestructura produce `inconclusive`.
6. `AttemptWorker` procesa la defensa pendiente: registra hallazgos deterministas, actualiza el estado necesario y `DefenseScheduler` propone o continúa un candidato.
7. Un run `finding_analysis` añade explicación al hallazgo. Otro run `validate_patch` espera la explicación opcional del parche y ejecuta las pruebas de seguridad/utilidad.
8. El scheduler activa un candidato validado cuando los intentos drenan y el padre coincide, pone en cuarentena memoria cuando corresponde y finaliza los hallazgos.

Fuentes: [core.py](../../backend/src/agent_zero/arena/core.py), [attempt_worker.py](../../backend/src/agent_zero/attempts/attempt_worker.py), [defense_scheduler.py](../../backend/src/agent_zero/patches/defense_scheduler.py) y [validation_handler.py](../../backend/src/agent_zero/patches/validation_handler.py).

Los eventos registran `attempt_queued`, herramientas, evaluación, hallazgo y transiciones de política. El outbox publica tras commit. Los workers consultan tablas; no existe un bus de comandos separado que dispare una función por cada evento.

## Quién decide

| Decisión | Servicio y criterio |
| --- | --- |
| Aceptar envío | `attempts`: autenticación, forma, contenido idempotente, frecuencia y cupos. |
| Elegir entorno | `routing`: ruta previa, violación, señales de Armor o negaciones repetidas. Devuelve `protected` o `honeypot`. |
| Autorizar efecto | Gateway: identidad/manifiesto y `BusinessPolicyEngine` sobre la versión fijada. |
| Confirmar violación | Oráculos: herramientas completadas, dueño, importes acumulados, escrituras de memoria y canarios. |
| Atribuir prevención | Evidencia de negación por un validador de negocio reconocido; un bloqueo genérico de Armor no basta. |
| Agrupar hallazgo | `FindingService`: fingerprint determinista de objetivo, herramienta y control ausente. |
| Elegir controles | `PolicyService`: unión del catálogo requerida por los objetivos observados. |
| Validar candidato | `ValidationRunner`: contrafactual y ocho casos en entornos limpios. |
| Activar o revertir | `PolicyService`: estado permitido, padre/hash, validación y drenaje. La reversión la solicita el operador. |
| Generar siguiente ataque | `CampaignHandler`: orden fijo de playbooks y presupuesto; la mutación LLM sólo cambia texto autorizado. |

## Estados y recuperación

`Attempt.status` y `Attempt.outcome` son distintos. El primero pasa por `queued`, `running` y `evaluated` o `inconclusive`; el segundo conserva el veredicto. `apparent_success` es una proyección provisional, no un veredicto persistido del oráculo.

La ruta de sesión no vuelve del señuelo al protegido. Repetir un intento desde Operación crea una sesión nueva; no cambia la ruta de su autor original. La versión de política no cambia a mitad de un intento.

Los leases excluyen la ejecución simultánea del mismo checkpoint; el fencing descarta una finalización de un propietario vencido. Una herramienta completada se recupera por identidad de operación. Una caída después del commit de un evento se recupera por el outbox. Un reset interrumpido se completa desde su registro durable antes de abrir trabajo nuevo.

## Validación y activación

El nivel 1 reconstruye la secuencia de efectos permitidos y exige que las acciones que sustentan la violación queden denegadas. El nivel 2 ejecuta el original —incluido su fixture controlado—, dos variantes y cinco tareas legítimas. La concurrencia máxima del ejemplo es ocho; no son ocho runs independientes de la cola general.

El candidato puede quedar `validating` mientras espera el drenaje. El scheduler vuelve a comprobarlo; no existe un temporizador de drenaje que cancele automáticamente todos los intentos. La activación cambia puntero, estado y evento en transacción. No deshace reembolsos anteriores.

`AnalyzerHandler` es de fondo. `PatchExplainer` no decide reglas ni validación, pero se espera antes de validar y puede añadir latencia. Su error se registra como asesoría `unavailable`; el validador continúa con los controles deterministas.

## Pruebas que preservan el flujo

```bash
cd backend
uv run pytest tests/arena/test_core_cycle.py tests/arena/test_multiturn.py tests/arena/test_control_concurrency.py tests/arena/test_transactional_events.py tests/runtime/test_run_leases.py -q
```

Consultar [attempts](./attempts.md), [patches](./patches.md), [policies](./policies.md), [events](./events.md) y la [matriz de pruebas](../pruebas/por-dominio.md) antes de modificar el orden o extraer un worker.
