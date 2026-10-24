---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: test/analizador-parches-eventos
pr: pendiente
estado: en revisión
dominios: [analyzer, attempts, policies, events]
requisitos: [CORE-04, CORE-05]
---

# Pruebas del analizador y del generador de parches: un hallazgo por fallo y sus eventos

## Qué cambió

Solo pruebas; el código de producción no cambia.

- Dos intentos con distinta redacción del mismo fallo (sesiones internas de `cust-ana` que consultan `B-2001`, con dos frases que la suite ya usaba) producen exactamente un hallazgo `OBJ-ORDER` / `get_order` / `order_belongs_to_session_customer` con los dos `attempt_ids` y la unión de la evidencia de ambos veredictos. La prueba cuenta los hallazgos; la de `test_admission_and_campaign.py` compara un conjunto de objetivos y no vería un duplicado.
- Cada intento evaluado deja un `attempt_evaluated` de operador (con el assessment) y uno público (`{"outcome": "apparent_success"}`, sin intento ni sesión). El hallazgo deja un solo `finding_opened` público con `finding_id` y `objective_id`, aunque llegue un segundo intento. Los tres tienen su fila en `product_event_delivery` con `delivered_at` y aparecen en `public_after`.
- `PolicyService.propose` deja un `patch_proposed` público con `version` y `finding_id`, entregado por el outbox, y no emite un segundo mientras hay un candidato pendiente. Se prueba con el hallazgo real del flujo y, parametrizado, para los tres objetivos del catálogo.
- El candidato guardado se proyecta sobre `policies/schemas.py:PolicyCandidate` y valida. La proyección (`tests/policies/support.py`) copia `parent_version`, `finding_ids`, `reason` y `status` de la fila y deriva tres campos que `PolicyVersion` no guarda: `policy_id` (`policy-NNNN` con la versión), `scope` (la herramienta del hallazgo) y `on_failure` (`block` en cada regla).

## Por qué

Una auditoría de los issues #9 y #10 encontró el comportamiento implementado en `analyzer/finding_service.py`, `attempts/attempt_execution_handler.py` y `policies/policy_service.py`, pero sin pruebas que lo fijen. `PolicyCandidate` solo se probaba con el ejemplo de arquitectura.

## Archivos

- `backend/tests/arena/test_findings_and_patch_events.py` (nuevo)
- `backend/tests/policies/test_policy_service.py` (nuevo)
- `backend/tests/policies/support.py` (nuevo)
- `docs/trazabilidad.md`: tablas "Requisito -> tests" (CORE-04, CORE-05) y "Garantías adicionales revisables".

## Cómo se verificó

En contenedor `python:3.12-slim-bookworm` con `uv sync --frozen`, desde `backend/`: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src tests scripts` y `uv run pytest -q`: ruff sin errores (636 archivos ya formateados), mypy sin problemas en 622 archivos y 1191 pasadas, 23 omitidas en 867,85 s. Todo offline, en SQLite; no se corrió contra Postgres.

Cada prueba nueva se comprobó contra una mutación temporal del código, aplicada sobre una copia del árbol dentro del contenedor:

| Mutación | Pruebas que fallan |
| --- | --- |
| La huella incluye el texto del intento | las tres de `test_findings_and_patch_events.py` (2 hallazgos en vez de 1) |
| Sin `attempt_evaluated` de operador | `test_evaluation_and_finding_events_go_through_the_outbox` |
| Sin `attempt_evaluated` público | `test_evaluation_and_finding_events_go_through_the_outbox` |
| Sin `finding_opened` | `test_evaluation_and_finding_events_go_through_the_outbox` |
| Sin `patch_proposed` | la de candidato real y las tres parametrizadas de `test_policy_service.py` |
| El candidato se guarda con `finding_ids` vacío | las mismas cuatro, con `ValidationError` de `PolicyCandidate` |

Sin mutación pasan las seis.

## Riesgos y efectos en otros frentes

- La conformidad con `PolicyCandidate` depende de la proyección del test, no de una validación en el código. Discrepancias entre el contrato y `PolicyVersion`:
  - `policy_id: str` no existe; la fila usa `version: int`.
  - `scope: ToolName` (una herramienta) no existe; las reglas de una versión son acumuladas y pueden cubrir varias herramientas (por ejemplo `order_belongs_to_session_customer` y `memory_key_allowlist` sobre una base ya parcheada).
  - `rules: list[PolicyRule]` lleva `on_failure`; la fila guarda `list[str]` sin acción.
  - `rules` exige al menos una regla del catálogo; un candidato sintetizado por flujo cambia `flow_rules` y puede dejar `rules` vacío o igual al padre.
  - La forma serializada (`policy_view`) agrega `version`, `content_hash`, `validation`, `created_at`, `activated_at`, `flow_rules` y `synthesis`, que `extra="forbid"` rechaza.
- Las pruebas de eventos identifican el `attempt_evaluated` público por su `dedup_key`, porque los eventos públicos no llevan el intento.

## Pendiente

- Decidir con Carlos si `PolicyCandidate` se ajusta a `PolicyVersion` o al revés; hasta entonces no hay validación del candidato en `policy_service.py`.
