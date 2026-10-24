# Agent Gateway: autorización de herramientas

Estado: implementado. Es el camino de ejecución que recibe un agente admitido mediante `ToolAccess`. Combina permisos del manifiesto y, en la arena, validadores de negocio de una versión fija.

## Archivos principales

| Código | Función |
| --- | --- |
| [agent_gateway.py](../../backend/src/agent_zero/agent_gateway/agent_gateway.py) | Coordina las etapas y registra el resultado. |
| [identity_stage.py](../../backend/src/agent_zero/agent_gateway/identity_stage.py) | Verifica la credencial y el scope de herramienta. |
| [manifest_source.py](../../backend/src/agent_zero/agent_gateway/manifest_source.py), [policy_engine.py](../../backend/src/agent_zero/agent_gateway/policy_engine.py) | Manifiesto aprobado, clasificación, región y frecuencia. |
| [business_policy.py](../../backend/src/agent_zero/agent_gateway/business_policy.py) | `CallContext`, `BusinessPolicy`, `BusinessDenial` y observador. |
| [argument_screening.py](../../backend/src/agent_zero/agent_gateway/argument_screening.py) | Armor sobre argumentos antes de invocar la herramienta. |
| [tool_registry.py](../../backend/src/agent_zero/agent_gateway/tool_registry.py), [tool_invocation.py](../../backend/src/agent_zero/agent_gateway/tool_invocation.py) | Registro y ejecución de handlers normales o contextuales. |
| [gateway_auditor.py](../../backend/src/agent_zero/agent_gateway/gateway_auditor.py) | Auditoría con datos redactados y razones de decisión. |

## Orden y contratos

`call_tool(token, tool_name, arguments, ..., call_context)` ejecuta identidad → política estática → política de negocio si hay contexto → Armor de entrada → herramienta → Armor de salida → auditoría. Una negación anterior a la herramienta impide su ejecución. Las decisiones son `allow`, `deny` y `redact`; [models.py](../../backend/src/agent_zero/agent_gateway/models.py) contiene las razones y etapas exactas.

La política estática comprueba permiso del manifiesto, clasificación suficiente, regiones del agente y del servidor, y límite de frecuencia por agente. No convertir un resultado `redact` en una negación: puede representar una operación permitida con PII retirada de la salida.

`CallContext` contiene intento, sesión, cliente autenticado, entorno, versión, run e identidad de operación. Lo construye el servidor. Una clave enviada dentro de los argumentos del modelo no reemplaza ese contexto. [GatewayToolProvider](../../backend/src/agent_zero/fleet/gateway_tool_access.py) vincula el acceso del handler a la credencial de su principal.

## Transacción de negocio y evidencia

[ProductCore](../../backend/src/agent_zero/arena/core.py) instala `BusinessPolicyEngine`, `TraceObserver` y un guard de [Environment.transaction](../../backend/src/agent_zero/victim/environments.py). En el escenario, ese guard usa `BEGIN IMMEDIATE`: lectura para autorizar y efecto comparten la reserva de escritura de SQLite, también con conexiones independientes.

La herramienta persiste resultado e identidad de operación antes de informar `tool_completed`. El evento se observa antes de Armor de salida: si una lectura indebida terminó y después se ocultó la respuesta, el oráculo sigue contando la acción. Mover ese evento detrás del filtro escondería evidencia.

La transacción del entorno y los eventos en `app.db` no forman una transacción distribuida. La recuperación se apoya en checkpoints e identidades de operación: repetir una operación completada recupera su resultado y permite reconstruir la observación.

## Pruebas

```bash
cd backend
uv run pytest tests/agent_gateway tests/fleet/test_gateway_tool_access.py -q
uv run pytest tests/arena/test_environment_transactions.py tests/arena/test_tool_retries.py tests/arena/test_business_objectives.py -q
```

| Prueba | Invariante |
| --- | --- |
| [test_agent_gateway.py](../../backend/tests/agent_gateway/test_agent_gateway.py) | Orden de etapas, negación antes del handler, redacción y errores. |
| [test_policy_engine.py](../../backend/tests/agent_gateway/test_policy_engine.py) | Manifiesto, clasificación, regiones y tasa. |
| [test_gateway_auditor.py](../../backend/tests/agent_gateway/test_gateway_auditor.py) | Decisión y razón auditadas sin PII. |
| [test_environment_transactions.py](../../backend/tests/arena/test_environment_transactions.py) | Dos pools independientes no gastan simultáneamente el mismo saldo; un reintento no duplica el reembolso. |
| [test_business_objectives.py](../../backend/tests/arena/test_business_objectives.py) | El efecto real determina la violación, incluso si el filtro de salida actúa después. |

## Límites y extensión

El proceso Python no es un sandbox: código con acceso al registro puede llamar un handler directamente. El límite de frecuencia de herramientas está en memoria por proceso y se reinicia al arrancar. Los argumentos se examinan por sus valores; el gateway genérico no sustituye el esquema cerrado de cada herramienta.

Para añadir una herramienta: definir DTO, registrarla, declarar su grant/scope, implementar autorización y efecto, añadir oráculo si crea un objetivo nuevo y probar denegación antes del efecto. Revisar [victim](./victim.md), [policies](./policies.md) e [identity](./identity.md) juntos.
