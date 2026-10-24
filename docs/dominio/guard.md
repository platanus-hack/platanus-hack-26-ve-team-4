# Dominio guard y contrato

Agent Zero para agentes de terceros. El dominio `contract` define el lenguaje con el que una empresa describe su agente; el dominio `guard` aplica el bucle invariante → hallazgo → regla → compuerta → activación sobre ese contrato. No depende del escenario Yummy: la arena sigue usando sus oráculos propios, y el contrato `yummy-soporte.yaml` describe ese mismo dominio en el formato genérico. La guía para empresas está en [integración](../integracion.md).

## Responsabilidad

- `contract/`: esquema, carga desde YAML, condiciones, procedencia léxica y variantes de ataque derivadas de cada invariante.
- `guard/`: verificación previa, informe de efecto, aprendizaje, administración de políticas y API HTTP.

## Puntos de entrada

| Archivo | Qué hace |
| --- | --- |
| `contract/schema.py` | `DomainContract`, `ToolContract`, `Invariant`, `PolicyRule`, `LegitimateCall`; valida coherencia al cargar y calcula el digest. |
| `contract/conditions.py` | Las cinco condiciones, `CallFacts` y `holds()`. `ACCEPTED_KINDS` fija qué condición admite cada tipo de argumento. |
| `contract/provenance.py` | Etiqueta cada argumento con `user`, `store`, `untrusted`, `memory` o `model`. Lo comparte `victim/provenance.py`. |
| `contract/loader.py` | `parse_contract` y `load_contracts(dir)`; rechaza YAML inválido y contratos duplicados. |
| `contract/attacks.py` | `violating_variant`: una llamada legítima mutada hasta romper un invariante. Base de las pruebas por contrato. |
| `guard/check_service.py` | `check`: contrato → dueño requerido → reglas activas → invariantes si `enforce_invariants`. Registra cada llamada. |
| `guard/learning_service.py` | `report` (efecto informado) y `learn_from_blocked` (intento frenado por invariante); crea hallazgo y versión. |
| `guard/orchestrator.py` | Une ambos: una denegación por invariante dispara el aprendizaje en la misma petición. |
| `guard/derivation.py` | Reglas deterministas: el invariante roto en todas sus herramientas y `untrusted_origin` para argumentos de baja integridad de herramientas con efecto. |
| `guard/synthesizer.py` | En `live`, el rol PATCHER propone reglas; si no pasan contrato y compuerta, se usan las derivadas. |
| `guard/enforcement.py` | `first_denial`, `gate` y las inyecciones simuladas. |
| `guard/admin_service.py` | Listado, activación de propuestas y reversión al padre. |
| `guard/router.py` | API bajo `/api/guard`. |

## API

| Ruta | Credencial | Uso |
| --- | --- | --- |
| `POST /api/guard/{id}/check` | `X-Guard-Key` | Decisión previa a la herramienta. |
| `POST /api/guard/{id}/effects` | `X-Guard-Key` | Efecto observado; idempotente por `call_id`. |
| `GET /api/guard/contracts` | operador | Contratos cargados con digest. |
| `POST /api/guard/contracts/validate` | operador | Valida un YAML sin instalarlo; hasta 100 KB. |
| `GET /api/guard/{id}/policies` · `findings` | operador | Historia de políticas y hallazgos. |
| `POST /api/guard/{id}/policies/{v}/activate` · `rollback` | operador | Control humano; 409 si el estado no lo permite. |

## Persistencia

Tres tablas en la base de la aplicación, creadas con el esquema común: `guard_calls` (hechos, decisión y efecto de cada llamada), `guard_policies` (versión, padre, estado, reglas, informe y digest del contrato; única por contrato y versión) y `guard_findings` (invariantes rotos y versión que los resolvió). Las escrituras que crean versiones toman la reserva de escritura (`serialize_write`), así que dos efectos simultáneos no producen dos versiones activas. La síntesis corre fuera de esa reserva y la versión se fusiona con el padre vigente al escribir, recalculando la compuerta.

Estados de una política: `active`, `proposed`, `superseded`, `rolled_back` y `rejected`. La versión 0 es implícita: sin reglas.

## Invariantes del dominio

- Ninguna regla se activa sin bloquear las llamadas que la originaron y conservar todas las tareas legítimas del contrato.
- Toda regla encaja con el tipo del argumento al que se aplica; se comprueba al cargar y al leer una política.
- Herramientas, argumentos o dueños desconocidos se deniegan.
- Cada versión hereda las reglas del padre activo.

## Pruebas

`tests/contract/` cubre esquema, condiciones, procedencia, carga y variantes. `tests/guard/test_router.py` recorre, para cada contrato de `backend/contracts/`, todos sus invariantes por HTTP: el ataque genera una política activa, el ataque repetido queda bloqueado por una regla aprendida y cada tarea legítima sigue pasando. También cubre la inyección pequeña bloqueada tras aprender de la grande, la reversión, el modo con aprobación, la idempotencia y los fallos cerrados. `tests/guard/test_dependencies.py` prueba la clave en producción.

```bash
cd backend && uv run pytest tests/contract tests/guard -q
```

La prueba de extremo a extremo con un agente fuera del proceso es `examples/guard/banco_demo.py` contra un servidor levantado.

## Extensión

- **Nuevo dominio**: añadir un YAML en `backend/contracts/`. Las pruebas parametrizadas lo recorren solas; deben pasar sin tocar código.
- **Nueva condición**: clase en `conditions.py`, entrada en `ACCEPTED_KINDS`, rama en `holds()`, cláusula en `guard/views.py` y mutación en `contract/attacks.py`.
- **Pendiente**: condiciones con ventana temporal, alta de contratos por API con firma, multi-inquilino, adaptadores MCP y de frameworks, y vista en la consola del operador.
