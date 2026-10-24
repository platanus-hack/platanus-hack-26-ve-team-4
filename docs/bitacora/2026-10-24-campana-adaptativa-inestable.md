---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: fix/campana-adaptativa-inestable
pr: pendiente
estado: en revisión
dominios: [prober, patches, evals]
requisitos: []
---

# Diagnóstico de la inestabilidad de la campaña adaptativa

## Qué cambió

Solo diagnóstico; no hay cambio de código. Explica por qué dos pruebas de `backend/tests/evals/test_adaptive_campaign.py` fallan cerca de 1 de cada 3 corridas, también en `main` (`63e1096`):

- `test_closed_rounds_are_announced_publicly_with_counters_only`;
- `test_adaptive_campaign_breaks_v0_then_holds_after_a_patch_with_exact_counts`.

## Por qué

### Causa 1: el reloj de pared del contenedor salta unos 222 s

`AdaptivePlanner._await_defense` (`prober/adaptive_planner.py`) mide la espera con el reloj de pared: `self._clock() - since`. `since` es el `updated_at` del último intento. En Docker Desktop de esta máquina, el reloj de pared de los contenedores oscila:

- vive unos 222 s **atrasado** respecto del host;
- cada 5 s salta **adelante** a la hora del host durante unos 150 ms y luego vuelve atrás.

Se midió con un contenedor `python:3.12-slim-bookworm` que lee `time.time()` cada 50 ms durante 60 s: 28 saltos, todos de +221,9 s o -221,8 s, cada 5 s aproximadamente. Al empezar, el host marcaba 19:32:27 UTC y el contenedor 19:28:46 UTC.

Cuando el planificador decide durante un salto adelante, ve `waited` de unos 222 s, más que `prober_round_close_wait_seconds` (90 s), y termina con `defender_did_not_close`. Por eso las corridas que fallan terminan antes: no esperan nada.

Con instrumentación temporal (un `print` por decisión, ya retirado) se registró:

- `test_closed_rounds...`, falla: activa la v1, la v2 queda en `validating` y el planificador decide `Finish: defender_did_not_close` con `waited=0:03:45`. La prueba duró 24 s.
- Otra falla de la misma prueba: v1 con 8 consultas y 1 violación, `Hold` con `waited=0,39 s`. La decisión siguiente da `waited=0:03:42` y `Finish: defender_did_not_close`.
- `test_adaptive_campaign_breaks...`: dos de tres fallas dan `waited=0:03:44` y `0:03:42`.
- En las decisiones consecutivas, `t` retrocede (por ejemplo, de 19:26:06 a 19:22:26) y luego vuelve a avanzar.

El valor de `waited` en cada falla coincide con el tamaño del salto del reloj.

### Causa 2, solo en `test_adaptive_campaign_breaks...`: la prueba compite con el `DefenseScheduler`

La tercera falla de esta prueba es otra: `assert await core.policies.activate(...)` da `False`, y la campaña sí sigue con la v1 activa. La prueba propone, valida y registra la validación de la v1 a mano. Entre `record_validation` y `activate`, `DefenseScheduler.tick` (`patches/defense_scheduler.py`) ve la candidata con `validation.passed` y la activa primero. Ese camino no mira `arena_auto_patch`. Cuando la prueba llama a `activate`, la v1 ya no está pendiente.

En la misma corrida, el worker registra en bucle `RuntimeError: coroutine raised StopIteration` desde `defense_scheduler.py:87`. La candidata de la prueba no tiene un hallazgo con su `finding_ids`, y `next(...)` no tiene valor por defecto. El worker lo registra y reintenta. No tumba la campaña, pero ensucia el registro.

### Clasificación

- **Causa 1:** la origina el entorno (el reloj de la VM de Docker Desktop), pero el producto se expone a ella al medir un intervalo con el reloj de pared. **(b) Afecta la demo en vivo** si corre en esta misma instalación de Docker: una campaña puede cerrar con `defender_did_not_close` mientras el parche está en `validating`. Otros usos de `fleet.clock` (TTL de credenciales, limitador, `Wait(until=...)` del runtime) también pueden comportarse mal. `[SUPUESTO]` No se midieron. En CI de Linux, con el reloj estable, no debería ocurrir.
- **Causa 2:** problema de la prueba (a), que choca con el `DefenseScheduler` al activar a mano. El `StopIteration` es un defecto menor del producto.

## Archivos

- `docs/bitacora/2026-10-24-campana-adaptativa-inestable.md` (esta entrada).

## Cómo se verificó

Todo en contenedor `python:3.12-slim-bookworm` con SQLite, en `63e1096` más la instrumentación temporal:

- `test_closed_rounds...`: 4 de 6 pasaron. Las 2 fallas son por la causa 1.
- `test_adaptive_campaign_breaks...`: 5 de 8 pasaron. 2 fallas son por la causa 1 y 1 por la causa 2.
- Medición del reloj: 28 saltos de ±222 s en 60 s.

No se corrió Postgres, ni `ruff`, `mypy` y `pytest` completos, porque no hay cambio de código.

## Riesgos y efectos en otros frentes

- Cualquier prueba o flujo que mida intervalos con `fleet.clock` dentro de este Docker Desktop puede fallar de forma intermitente. Las mediciones de tiempo de las corridas de prueba tomadas con `date` en el contenedor tampoco son confiables: aparecieron duraciones de 262 s y -172 s.

## Pendiente

- Corregir el reloj de la VM de Docker Desktop, por ejemplo con `wsl --shutdown` y reiniciando Docker Desktop. Hay que coordinarlo con el usuario porque detiene la pila `agent-zero`. Después, volver a medir con el mismo contenedor y repetir las dos pruebas 15 veces.
- Proteger la espera del planificador contra saltos del reloj de pared: medir la espera con un reloj monótonico inyectable desde la primera vez que el planificador ve un `since`. Adaptar `tests/prober/test_adaptive_planner.py` y agregar una prueba con un salto de +222 s.
- Evitar la carrera en `_activate_patch_for_a_break`: que la prueba deje activar al `DefenseScheduler` y espere la v1 activa, o que el scheduler respete `arena_auto_patch`. Hay que decidir con Carlos cuál es el comportamiento esperado.
- Dar un valor por defecto al `next(...)` de `defense_scheduler.py:87` cuando la candidata no tiene hallazgo.
