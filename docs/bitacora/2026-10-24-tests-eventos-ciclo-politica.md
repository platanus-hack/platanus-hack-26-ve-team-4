---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: test/eventos-ciclo-politica
pr: pendiente
estado: en revisión
dominios: [policies, patches, events]
requisitos: [CORE-04, CORE-05]
---

# Pruebas de los eventos de validación, activación y reversión de políticas (issue #11)

## Qué cambió

Solo cambió código de prueba y documentación. No se tocó `backend/src`.

Se añadieron tres pruebas en `backend/tests/arena/test_policy_lifecycle_events.py`:

- **Ciclo completo por HTTP.** Un ataque real llega a hallazgo confirmado, se propone la versión 1, el planificador la valida, la activa y la finaliza, y el operador la revierte con `POST /api/operator/policies/1/rollback`. Comprueba que `patch_validated`, `policy_activated` y `policy_rolled_back` aparecen una sola vez cada uno, con su versión y sus datos. Confirma que cada uno se entrega por el outbox (`delivered_at`), que el despachador lo audita una sola vez con su `event_id`, que el feed público (`public_after`) trae los mismos datos y que ningún evento del ciclo va al canal de operador. Al final, la versión 1 queda `rolled_back`, la 0 queda `active` y el hallazgo queda `reopened`.
- **Validación fallida.** Con los workers parados, `record_validation` con `passed: false` publica `patch_validated` con `passed: false` y no activa nada. Un segundo informe (`passed: true`) se ignora porque la política ya no está en validación, y la activación y la reversión se rechazan.
- **Activación y reversión repetidas.** Una segunda activación responde sin volver a publicar, dos finalizaciones no duplican `policy_activated`, la reversión publica una vez con la versión 0 y una segunda reversión falla por la transición de estado.

## Por qué

El issue #11 pide que el código emita `patch_validated`, `policy_activated` y `policy_rolled_back`. Solo `policy_activated` tenía prueba, en `backend/tests/arena/test_control_concurrency.py`, y solo para la concurrencia. Ningún test comprobaba las tres emisiones en el ciclo real ni que cada una sale una vez, por el outbox y en el canal correcto.

## Archivos

- `backend/tests/arena/test_policy_lifecycle_events.py`: las tres pruebas.
- `docs/trazabilidad.md`: el archivo se añade a las filas CORE-04 y CORE-05 de la tabla de requisitos, y una fila nueva en "Garantías adicionales revisables".
- `docs/bitacora/2026-10-24-tests-eventos-ciclo-politica.md`: esta entrada.

## Cómo se verificó

Comando de verificación, en contenedor (en Windows, pytest y mypy nativos fallan por `fcntl`), con el volumen de venv `smoke-pr-venv-t11`:

```
MSYS_NO_PATHCONV=1 timeout 1500 docker run --rm -v C:/dev/Work_space/Hack/wt-tests-11-12:/repo -v smoke-pr-venv-t11:/venv -w /repo/backend -e PYTHONUTF8=1 -e UV_PROJECT_ENVIRONMENT=/venv -e UV_LINK_MODE=copy python:3.12-slim-bookworm sh -c "pip install -q uv==0.12.7 && uv sync -q --frozen && uv run ruff check && uv run ruff format --check && uv run mypy src tests scripts && uv run pytest -q -p no:cacheprovider tests/arena/test_policy_lifecycle_events.py"
```

Resultado de la última corrida limpia: `ruff check` sin errores, `ruff format --check` con 640 archivos ya formateados, `mypy src tests scripts` con 626 archivos sin problemas, y `pytest`: 3 passed en 9.05 s.

Antes de esa corrida, `ruff` marcó dos `pytest.raises(ValueError)` demasiado amplios (PT011). Se corrigieron con `match="Solo se revierte la versión activa"`.

Mutaciones. Cada una se aplicó sobre una copia de `backend` dentro del contenedor (`/tmp/m`), nunca sobre el worktree ni sobre un commit. Línea base: 3 passed.

| Mutación | Cambio en `backend/src` | Pruebas que fallan |
| --- | --- | --- |
| M1 | `finalize` usa `dedup_key` `:finalized` en vez de `:activated` | `test_validation_activation_and_rollback_each_announce_once_through_the_outbox`, `test_repeated_activation_and_rollback_do_not_announce_again` |
| M2 | `rollback` publica `version` (la revertida) en vez de `target` | `test_validation_activation_and_rollback_each_announce_once_through_the_outbox`, `test_repeated_activation_and_rollback_do_not_announce_again` |
| M3 | `deliver_pending` deja `delivered_at` vacío para `POLICY_ROLLED_BACK` | `test_validation_activation_and_rollback_each_announce_once_through_the_outbox`, `test_repeated_activation_and_rollback_do_not_announce_again` |
| M4 | `rollback` emite `POLICY_ROLLED_BACK` como `OPERATOR` | `test_validation_activation_and_rollback_each_announce_once_through_the_outbox`, `test_repeated_activation_and_rollback_do_not_announce_again` |
| M5 | `record_validation` no emite `patch_validated` | las tres pruebas |
| M6 | `record_validation` publica `passed: true` siempre | `test_rejected_validation_announces_passed_false_once_and_nothing_activates` |
| M7 | `rollback` sin `dedup_key` | solo `test_validation_activation_and_rollback_each_announce_once_through_the_outbox`, por su aserción sobre `dedup_key` |

Sin mutación pasan las tres pruebas.

La mutación M7 no la detecta la prueba de repetición (`test_repeated_activation_and_rollback_do_not_announce_again`). Una segunda reversión la frena la transición de estado antes de llegar al evento, así que el `dedup_key` no interviene ahí. Lo detecta solo la primera prueba, que compara el `dedup_key` del evento.

Pruebas de trazabilidad: ver la corrida de `tests/test_traceability.py` en el commit de documentación.

## Riesgos y efectos en otros frentes

- `finalize` vuelve a encolar `POLICY_ACTIVATED` con la misma `dedup_key` que `activate`. Solo queda un evento porque el outbox deduplica por esa clave. Si alguien cambia esa clave, el evento se duplica, y la prueba lo detecta (M1).
- `policy_rolled_back` lleva en `policy_version` y en `data` la versión a la que vuelve la política (la padre, 0). Su `dedup_key` lleva la versión revertida (`policy:1:rolled_back`). Son datos distintos a propósito y no deben confundirse.
- Estos tres eventos no tienen copia para el operador. Van solo al canal público, que alimenta el historial de `public_after`.
- Las pruebas no atraviesan el flujo SSE por HTTP. Leen `public_after`, que es la fuente de su historial.

## Pendiente

- Si se quiere, cubrir por HTTP el flujo SSE de estos tres tipos de evento.
- Las cifras de la suite completa no están en esta entrada. Se registran en la respuesta del track; si el líder las pide en la bitácora, se añaden en un commit nuevo.
