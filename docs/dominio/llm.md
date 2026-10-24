# LLM: proveedores, origen y presupuestos

Estado: implementado. `LlmGateway` entrega modelos instrumentados a los cinco roles; el bucle de herramientas, las mutaciones y las explicaciones usan ese acceso común. Las decisiones de seguridad y los oráculos permanecen en servicios deterministas.

## Entrada y configuración

| Archivo | Responsabilidad |
| --- | --- |
| [factory.py](../../backend/src/agent_zero/llm/factory.py) | Construye proveedor, wrappers, ledger y límites. |
| [gateway.py](../../backend/src/agent_zero/llm/gateway.py), [structured.py](../../backend/src/agent_zero/llm/structured.py) | Acceso por rol y salida Pydantic con presupuesto de reparación. |
| [catalog.py](../../backend/src/agent_zero/llm/catalog.py) | Modelo por rol, esfuerzo, thinking y máximo de salida. |
| [instrumented_model.py](../../backend/src/agent_zero/llm/instrumented_model.py), [call_watch.py](../../backend/src/agent_zero/llm/call_watch.py) | Uso, origen, resultado, latencia y error por llamada. |
| [limits.py](../../backend/src/agent_zero/llm/limits.py), [quota.py](../../backend/src/agent_zero/llm/quota.py), [breaker.py](../../backend/src/agent_zero/llm/breaker.py) | Cupos, presupuesto y circuito por rol. |
| [retrying_model.py](../../backend/src/agent_zero/llm/retrying_model.py) | Reintentos transitorios con backoff y jitter. |
| [ledger.py](../../backend/src/agent_zero/llm/ledger.py), [pricing.py](../../backend/src/agent_zero/llm/pricing.py) | JSONL de llamadas y estimación de coste según tarifas configuradas. |
| [context.py](../../backend/src/agent_zero/llm/context.py), [traced_model.py](../../backend/src/agent_zero/llm/traced_model.py) | Scope de sesión/intento/campaña, versión de prompt y traza. |

`AGENT_ZERO_LLM_MODEL` fija el modelo base y `AGENT_ZERO_LLM_ROLE_MODELS` permite overrides por rol. `victim`, `decoy` y `prober` usan el perfil de volumen; `analyzer` y `patcher`, el perfil de explicación. Consultar el catálogo al cambiar de modelo; esta guía no promete compatibilidad de parámetros con cualquier proveedor.

## Modos y evidencia

| Modo | Comportamiento y origen |
| --- | --- |
| `demo` | `DemoModel`, intérprete determinista que propone llamadas a las herramientas reales del escenario. Origen `simulated`; no inventa tokens ni coste. |
| `offline` | `PlaybackModel` inyectado en pruebas. Un guion vacío falla explícitamente; no instala demo automáticamente. Origen `simulated`. |
| `live` | Adaptador Anthropic con clave de servidor; origen `live`. |
| `record` | Llamadas reales más cassette guardada; origen `live`. |
| `replay` | Consume entradas grabadas por rol/tipo/DTO; origen `replayed`. No llama al proveedor. |

El valor base de `Settings` es `offline`; `.env.example` y Compose seleccionan `demo` para que el arranque de demostración funcione sin clave. Los comandos Make cargan el `.env` de la raíz; `Settings()` directamente busca `.env` desde el directorio de trabajo.

La clave procede de `AGENT_ZERO_LLM_API_KEY` o `ANTHROPIC_API_KEY` en los modos reales. `replay` necesita una cassette compatible en `AGENT_ZERO_LLM_CASSETTE_PATH`; las entradas se consumen secuencialmente, no se buscan por equivalencia del prompt. No usarla para medir generalización frente a mensajes nuevos.

## Límites y fallos

Se reservan llamadas por día, sesión y campaña. Los tokens de campaña se cargan si el proveedor reporta uso. El límite USD se comprueba antes de la siguiente llamada y se incrementa con el coste calculado al terminar; no es un límite duro de facturación de la cuenta del proveedor ni reserva el coste máximo de llamadas simultáneas.

Los contadores generales de llamadas/tokens y los breakers viven en memoria por proceso. Al arrancar, el ledger reconstruye gasto USD LIVE, pero no esos contadores. [Prober](./prober.md) mantiene aparte su plan durable de mutaciones/intentos; [evals](./evals.md) cuenta llamadas por ID de evaluación desde el ledger para su `max_calls`. No presentar los límites generales como una cuota global entre varias réplicas.

El wrapper de reintento recoge el stream completo antes de entregarlo, para evitar emitir fragmentos de dos intentos del proveedor. La instrumentación envuelve ese wrapper: una reserva y una entrada del ledger pueden incluir varios intentos HTTP. La cuota de llamadas instrumentadas no es un contador exacto de solicitudes facturables ni mide necesariamente el uso de intentos fallidos. Un error, una negativa del modelo o un límite no activa un fallback simulado. Las ejecuciones incompletas se conservan como errores o inconclusos según el servicio consumidor.

## Pruebas reproducibles

```bash
cd backend
uv run pytest tests/llm -q
uv run pytest tests/victim/test_model_turn.py tests/evals/test_unavailable_provider.py -q
```

La suite de LLM tiene 79 casos recogidos, de los cuales dos requieren autorización explícita para gastar API. Con `AGENT_ZERO_LLM_LIVE_SMOKE` ausente se omiten. Para repetir sólo esas dos pruebas, desde la raíz y con clave local configurada:

```bash
set -a
. ./.env
set +a
cd backend
AGENT_ZERO_LLM_LIVE_SMOKE=1 uv run pytest tests/llm/test_live_provider.py -q
```

Para el ciclo completo, usar el [ensayo LIVE](../pruebas/evidencias.md), cuyo comando acota gasto y crea datos temporales. No necesita abrir la arena persistente del equipo.

| Pruebas | Garantía |
| --- | --- |
| [test_instrumented_model.py](../../backend/tests/llm/test_instrumented_model.py), [test_reporting.py](../../backend/tests/llm/test_reporting.py) | Uso y coste desconocidos permanecen desconocidos; origen separado. |
| [test_limits.py](../../backend/tests/llm/test_limits.py), [test_quota.py](../../backend/tests/llm/test_quota.py), [test_breaker.py](../../backend/tests/llm/test_breaker.py) | Límites, reservas y recuperación del circuito. |
| [test_retrying_model.py](../../backend/tests/llm/test_retrying_model.py) | Reintento transitorio acotado y stream consistente. |
| [test_cassette_model.py](../../backend/tests/llm/test_cassette_model.py), [test_recording_model.py](../../backend/tests/llm/test_recording_model.py) | Grabación, reproducción y agotamiento explícito. |
| [test_structured.py](../../backend/tests/llm/test_structured.py) | Esquema y reparación limitada de salida. |
| [test_model_turn.py](../../backend/tests/victim/test_model_turn.py) | JSON fragmentado, IDs, bloques incompletos y cotas antes de ejecutar efectos. |

## Continuidad

Prioridades: cuotas persistentes compartidas, sincronización del ledger entre procesos y política ante modelos sin tarifa conocida. El JSONL usa un lock de hilo por instancia, sin el protocolo de archivo firmado de auditoría; no atribuirle esas garantías. Un nuevo proveedor debe implementar el contrato de streaming y salida estructurada, conservar el origen y pasar las pruebas de streams truncados antes de una prueba LIVE con presupuesto.
