---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: feat/evidencia-evaluacion
pr: pendiente
estado: en revisión
dominios: [evals]
requisitos: []
---

# Repetir la evaluación amplia DEMO sobre los fixtures actuales

## Qué cambió

Se agregó `artifacts/core-evaluation/demo-270-2026-10-24-yummy.json`, con su `.json.sha256`. Es la misma comparación de `demo-270.json`: políticas 0 y 3, 45 casos, tres repeticiones, 270 ejecuciones, en modo DEMO y sin honeypot. Esta vez corre sobre los datos actuales.

`demo-270.json` y su hash no se tocaron. En `docs/pruebas/evidencias.md` sigue con su fila, ahora con la aclaración de que corresponde a los fixtures anteriores.

| Medida | `demo-270.json` | `demo-270-2026-10-24-yummy.json` |
| --- | --- | --- |
| Evaluación | `eval-0b4b840a0609` | `eval-4f9375e1912d` |
| Commit | `aed15dd` (equivale a `20f97a7`), árbol modificado | `63e10960319fa6beef292b717a4dc2e251e4edb5`, árbol limpio |
| `fixture_hash` | `26095a2e…6d5fd0` | `0fe4044f383bdc0606fa07bd9983b52746232a8ce046ae72fb99abcf2d1aebf9` |
| `suite_hash` y hashes de políticas 0 y 3 | `9a4a0cd3…`, `c38b8b5c…`, `f83251bc…` | Idénticos |
| Violaciones 0 → 3 | 90/90 → 0/90 | 90/90 → 0/90 |
| Utilidad por versión | 45/45 | 45/45 |
| Inconclusos | 0 | 0 |
| Llamadas `simulated` | 732 | 732 |

El resultado de cada caso, versión y repetición es idéntico en las 270 ejecuciones. El `state_hash` cambia en cada ejecución en los dos JSON, porque incluye canarios aleatorios y el `operation_id` de los reembolsos, así que no sirve para compararlos. El texto de `reply` difiere en 201 ejecuciones: 63 solo por identificadores y canarios aleatorios, y 138 porque `get_order` ahora devuelve nombre, comercio y direcciones.

## Por qué

`demo-270.json` guarda un `fixture_hash` que ya no coincide con `evals/suite.py:fixture_hash()`. Desde que se generó entraron los comercios de Yummy (#24), el origen y destino de entrega (#29) y los nombres de clientes (#34). Hacía falta evidencia sobre los datos actuales sin reescribir la anterior, como pide `docs/continuidad.md`.

Las cifras no cambian porque los seis pedidos conservan identificador, dueño, total, estado y saldo. Cambian los artículos y el dominio del correo, y se agregan comercio, direcciones y nombre. Ningún oráculo ni expectativa de utilidad lee esos campos.

## Cómo se generó

Se siguió el procedimiento HTTP de `docs/evaluacion.md` §9 en un contenedor `python:3.12-slim-bookworm`, con este orden:

1. Se clonó limpio el commit `63e1096` desde un `git bundle` de la rama.
2. Se corrió `uv sync --frozen`.
3. Se levantó `uvicorn agent_zero.main:create_app` con SQLite en un directorio fuera del árbol, sin publicar puertos ni cargar `.env`.
4. Se lanzó la campaña `{"max_attempts":6,"generation":"llm","max_mutations":6}` y se esperó a que la política activa estuviera validada y tuviera los tres controles del catálogo. Fue la versión 3.
5. Se corrió `uv run python -m agent_zero.evals --base-url http://127.0.0.1:8000 --before 0 --after 3 --repetitions 3 --max-calls 1200 --output …/demo-270-2026-10-24-yummy.json`.

El servidor usó los valores de `.env.example` (incluido `AGENT_ZERO_LLM_MODE=demo`), salvo los secretos (aleatorios y de un solo uso) y dos variables:

- `AGENT_ZERO_ARENA_FLOW_SYNTHESIS=false`. Con `true`, que es el valor de `.env.example`, un primer intento mitigó pedido y reembolso con `flow_rules` sintetizadas. La versión activa quedó con un solo control del catálogo y la espera de §9 no se cumplía (termina con error a los 300 s). `demo-270.json` registra los tres controles del catálogo en su política 3.
- `AGENT_ZERO_GATEWAY_RATE_LIMIT_PER_MINUTE=10000`, el mismo valor que fija `scripts/verify_live.py`. El valor por defecto es 60 llamadas por minuto, contadas por agente, y las 270 ejecuciones comparten `soporte-tienda`. Con 60 se completó una corrida: 187 de las 270 ejecuciones recibieron `rate_limited`, la política 0 quedó con 26/90 violaciones y la utilidad bajó a 16/45. Esas denegaciones no son defensas, así que esa corrida no vale como comparación. Se archivó fuera del repositorio y no se commitea. El límite por agente ya figuraba como pendiente en [la bitácora de la traza v2](./2026-10-24-traza-herramientas-v2.md).

Una corrida previa con estas mismas variables y cifras se descartó porque el reloj de Windows estaba desincronizado: estaba 222 s adelantado y con `w32time` detenido, y producía latencias de ±222 s. La evidencia guardada se generó después de sincronizar el reloj. Sus latencias por ejecución van de 0,10 a 0,56 s, sin valores negativos, y la creación y el cierre fueron entre las 19:49:03 y las 19:50:37 UTC.

## Archivos

| Archivo | Cambio |
| --- | --- |
| `artifacts/core-evaluation/demo-270-2026-10-24-yummy.json` y `.json.sha256` | Evidencia nueva. SHA-256 `ed6623b94a80839a5d6f5d712a19dbf0190da7128ec4444cfc4568197ed27459` |
| `docs/pruebas/evidencias.md` | Fila nueva, aclaración sobre `demo-270.json`, sección de la repetición, hash y variables para repetirla |
| `docs/evaluacion.md` | §8 cita la repetición; §9 indica las dos variables del servidor |
| `docs/nucleo.md`, `docs/continuidad.md` | Mención de la repetición junto a las cifras |

## Cómo se verificó

- El `.sha256` coincide con el JSON (`sha256sum -c`).
- El `fixture_hash` del JSON es igual al que imprime `fixture_hash()` en `63e1096`.
- `commit` es `63e1096` y `working_tree_dirty=false`.
- Comparación por caso, versión y repetición contra `demo-270.json`: no hay diferencias.
- No se encontraron credenciales, claves, el secreto de operador ni variables `AGENT_ZERO_` en el JSON.
- Checks en el contenedor `python:3.12-slim-bookworm` sobre esta rama: `ruff check` pasó; `ruff format --check` dejó los 631 archivos sin cambios; `mypy src tests scripts` no encontró errores en 617 archivos; `pytest tests/test_traceability.py tests/evals` aprobó 38 pruebas en 494 s.

## Riesgos y efectos en otros frentes

- El valor 10000 del gateway no queda registrado en el metadata del JSON: el informe no guarda ese ajuste. Por eso se documenta aquí y en `evidencias.md`. [SUPUESTO] `demo-270.json` también corrió con un límite alto: 270 ejecuciones en 23 s superan con creces 60 llamadas por minuto, y su metadata tampoco lo registra.
- `.env.example` activa la síntesis de flujos. Quien siga §9 con ese archivo sin cambiarlo no obtiene los tres controles del catálogo.
- La evidencia sigue siendo DEMO, con el proveedor `demo-rule-engine-v1`. No mide eficacia de un LLM real.

## Pendiente

- Para Carlos: `.env.example` trae `AGENT_ZERO_ARENA_FLOW_SYNTHESIS=true`, y con eso la espera de `docs/evaluacion.md` §9 nunca se cumple y termina con error a los 300 s, porque la política activa mitiga con `flow_rules` y no reúne los tres controles del catálogo. Decidir si `.env.example` o §9 fijan `false` para la evaluación, o si la espera debe aceptar también `flow_rules`.
- El límite del gateway por agente para la evaluación sigue pendiente, como en la traza v2.
