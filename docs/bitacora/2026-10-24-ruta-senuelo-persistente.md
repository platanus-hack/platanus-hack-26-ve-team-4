---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: test/ruta-senuelo-persistente
pr: pendiente
estado: en revisión
dominios: [routing, attempts, arena]
requisitos: [CORE-06]
---

# Test de la ruta señuelo persistente ante un intento explícito de volver al protegido

## Qué cambió

Se agrega `backend/tests/arena/test_sticky_honeypot_route.py` con tres tests. No cambia código de producción.

- `test_armor_diverted_session_stays_in_honeypot_when_asking_for_real_support`: una sesión desviada por Armor en el primer turno (texto de `test_reply_composer.py`, bloqueado por Armor) recibe el pedido de volver al soporte real, el mismo texto del turno `honeypot-3` de `backend/scripts/live_flow.py`. El turno sale `route=honeypot`, `outcome=contained_honeypot`, la única herramienta completada es `get_order` en `honeypot` con canario `AZH_` y ningún `AZP_` aparece en la vista de operador. La vista pública no trae `route` y muestra `apparent_success`. La sesión sigue en `honeypot` y sin una segunda transición (`route_changed` por motivo `armor`).
- `test_route_or_environment_field_is_rejected_without_creating_an_attempt`: un `POST /api/attempts` con `route` o con `environment` da 422 con un único error `extra_forbidden` en `body`, no crea intento y no consume la clave `back`. Después, el mismo envío válido con esa clave sale en `honeypot` y la sesión tiene dos intentos.
- `test_violation_diverted_session_stays_in_honeypot_when_asking_for_real_support`: paridad con `test_core_cycle.py::test_subsequent_turn_is_permanently_contained`. Un ataque a un pedido ajeno da `confirmed_violation` en `protected`; el turno siguiente ya sale en `honeypot` (la transición ocurre al admitirlo); el pedido de volver al soporte real sale también en `honeypot`. El motivo registrado es `confirmed_violation`.

Documentación:

- `docs/trazabilidad.md`: el enlace al test nuevo en la fila de CORE-06 y una frase en la nota de CORE-01/CORE-06. No cambian las columnas de estado ni se crean IDs.
- `docs/dominio/routing.md`: el archivo en el comando de pruebas, dos filas en la tabla de pruebas y una frase en el párrafo del ensayo LIVE.
- `docs/dominio/attempts.md`: el archivo en el comando de pruebas y una fila nueva para los campos extra.

## Por qué

El issue #12 pide como criterio "Un intento explícito de volver al protegido falla". Hasta ahora solo lo comprobaba el script LIVE `backend/scripts/live_flow.py` (turno `honeypot-3`), que necesita un proveedor real. Este test fija lo mismo con proveedor simulado y en la suite normal.

El test de 422 cubre que el esquema `AttemptCreate` (`extra="forbid"`) rechaza `route` y `environment` antes de crear nada. Sin ese rechazo, un cliente podría pedir un entorno de forma explícita.

## Archivos

- `backend/tests/arena/test_sticky_honeypot_route.py` (nuevo, requisito `CORE-06`)
- `docs/trazabilidad.md`
- `docs/dominio/routing.md`
- `docs/dominio/attempts.md`

Commits locales en la rama: `d5babed` (tests 1 y 3) y `a323cc1` (test 2).

## Cómo se verificó

Contenedor `python:3.12-slim-bookworm` con `uv` 0.12.7, desde `backend/`, y volumen de entorno propio `smoke-pr-venv-12` sincronizado con `uv sync --frozen`:

```bash
uv run ruff check && uv run ruff format --check && uv run mypy src tests scripts && uv run pytest -q -p no:cacheprovider <rutas>
```

| Paso | Rutas | Resultado |
| --- | --- | --- |
| Paso 1 (`d5babed`) | `tests/arena/test_sticky_honeypot_route.py tests/arena/test_core_cycle.py` | ruff sin hallazgos; `640 files already formatted`; mypy `Success: no issues found in 626 source files`; pytest `5 passed in 33.01s` |
| Paso 2 (`a323cc1`) | mismo archivo más `test_core_cycle.py` | ruff, format y mypy igual; pytest `6 passed in 38.51s` |

Cada test se comprobó rompiendo a propósito el comportamiento que cubre. Se aplicó el cambio sobre el archivo del worktree, se corrió pytest y se restauró con `git checkout --`. Después de cada cambio, `git status --short backend/src` quedó vacío.

| Cambio temporal | Test que falló | Dónde falló |
| --- | --- | --- |
| M1: se borran las líneas 32-33 de `route_decision_service.py` (ruta fija), con solo los tests 1 y 3 | `test_armor_diverted_session_stays_in_honeypot_when_asking_for_real_support` | `assert_contained`: `'protected' == 'honeypot'` en la ruta del turno `back`. El test de violación pasa. |
| M1: igual, con los tres tests | `test_armor_diverted_session_...` y `test_route_or_environment_field_...` | `assert_contained`: `'protected' == 'honeypot'`, en el turno `back` y en el intento aceptado tras los 422. El test de violación pasa. |
| M2: `extra="forbid"` cambiado por `extra="ignore"` en `attempts/schemas.py` (tres tests) | `test_route_or_environment_field_is_rejected_without_creating_an_attempt` | `assert response.status_code == 422`: `202 == 422`. Los otros dos pasan. |
| M3: `environment=attempt.route.value` cambiado por `environment="protected"` en `attempt_query_service.py` (archivo con los tests 1 y 3) | `test_armor_...` y `test_violation_...` | `assert_contained`: `'not_achieved' == 'contained_honeypot'`. La comprobación de `environment` no llegó a ejecutarse porque el `outcome` falló antes. |

Observaciones sobre M1:

- El test de violación sigue pasando con la ruta fija borrada. Según el código de `route_decision_service.py` (líneas 37-57), `needs_diversion()` vuelve a devolver `True` por la violación previa y el `dedup_key` `{sesión}:diverted` evita un segundo `route_changed`. Eso explica el resultado observado. [SUPUESTO: el mecanismo del `dedup_key` no se comprobó con una prueba separada, solo con el resultado del test y la lectura del código.]
- Por eso los tests de la vía armor son los que aíslan la ruta fija.

No se corrió M3 sobre el archivo del paso 2. Según la especificación, en ese paso solo se corren M2 y M1. [SUPUESTO: M3 también haría fallar el test de 422, porque usa `assert_contained`; no se comprobó.]

Con la documentación ya aplicada, la misma comprobación en contenedor corre `tests/test_traceability.py` y `tests/arena/test_sticky_honeypot_route.py`: ruff y format sin hallazgos, mypy `Success: no issues found in 626 source files`, pytest `6 passed in 19.33s` (3 de trazabilidad y 3 del archivo nuevo). `git diff --check` no marca errores.

## Riesgos y efectos en otros frentes

- La vía armor depende de que la heurística de Armor siga bloqueando el texto reutilizado de `test_reply_composer.py`. Si deja de hacerlo, `divert_by_armor` falla con un mensaje claro en el primer `assert` (`first["route"]`), no en el test de 422.
- El test de violación no distingue la ruta fija de `needs_diversion`. Ese caso no es un defecto del test: la ruta fija se comprueba con el test de armor.
- El test usa `ScenarioPlayback` (proveedor simulado). No prueba un modelo real.
- No se tocó la política de entrada de `POST /api/attempts`: el test fija el rechazo de `route` y `environment`, no un cambio de esquema.

## Pendiente

- La evidencia con proveedor real sigue siendo el ensayo LIVE (`backend/scripts/live_flow.py`, turno `honeypot-3`).
- Abrir la PR con esta entrada cuando se decida integrarla. Hasta entonces, `pr: pendiente`.
