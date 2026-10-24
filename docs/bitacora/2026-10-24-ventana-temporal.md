---
fecha: 2026-10-24
autor: "@usuario"
rama: worktree-agent-a143ca38560c437d6
pr: ninguno  # push directo a main
estado: integrado
dominios: [guard, contract]
requisitos: []
---

# Condición con ventana temporal en el contrato del Guard

## Qué cambió

- Nueva condición `window_exceeds` en la gramática cerrada: se cumple cuando el valor del argumento en esta llamada, más la suma del mismo argumento en las llamadas previas permitidas del mismo sujeto a la misma herramienta dentro de `window_seconds`, supera `limit`. Solo admite argumentos `amount`. `limit` debe ser mayor que 0 y `window_seconds` va de 60 a 2 592 000.
- `CallFacts` recibe `totals` (clave `argumento@ventana`, por defecto vacío). Una llamada sin historia solo cumple la condición si su valor, por sí solo, supera el límite.
- `GuardCheckService` calcula los totales de cada condición de ventana presente en las reglas activas o en los invariantes que cubren la herramienta, dentro de la misma transacción que registra la llamada. La transacción toma el candado de escritura (`serialize_write`) antes de la primera lectura, así que dos checks concurrentes no pasan a la vez el tope, en SQLite ni en Postgres.
- Los hechos guardados conservan `totals`. El reporte de efectos y el aprendizaje de una llamada bloqueada por invariante evalúan con los mismos hechos que vio el check.
- `violating_variant` genera una variante con valor `limit + 1`; la vista legible muestra "monto acumulado en 24 h > 1000"; el prompt del sintetizador nombra la condición nueva y recibe los totales de la llamada.
- El contrato `banco-transferencias` gana el invariante `tope-diario` (1000 USD en 86 400 s sobre `transferir`).

## Por qué

Hasta ahora cada invariante miraba una llamada aislada. Un atacante podía repartir una transferencia grande en varias bajo el tope por llamada. El tope acumulado cubre ese patrón sin salir de la gramática agnóstica.

## Archivos

- `backend/src/agent_zero/contract/conditions.py`, `attacks.py`
- `backend/src/agent_zero/guard/window_totals.py` (nuevo), `check_service.py`, `learning_service.py`, `facts.py`, `views.py`, `synthesizer.py`
- `backend/contracts/banco-transferencias.yaml`
- Pruebas: `backend/tests/contract/test_conditions.py`, `backend/tests/guard/test_window_totals.py`, `test_views.py`, `test_router.py`

## Cómo se verificó

Desde `backend/`: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src tests scripts` y `uv run pytest -q` (1168 pasadas, 23 omitidas). Todo offline. El test parametrizado que recorre cada invariante de cada contrato pasa sin cambios con `tope-diario`. Un test de router comprueba que dos transferencias de 450 se permiten, la tercera se bloquea con `invariant:tope-diario`, aprende una política que pasa la compuerta y otro sujeto no se ve afectado. No se ejecutó contra Postgres [SUPUESTO: el candado es el mismo `acquire_write_lock` que usan los demás servicios].

## Riesgos y efectos en otros frentes

- Todo `check` toma ahora el candado de escritura al abrir la transacción (antes no lo tomaba). Serializa los checks de todos los contratos; el costo es una consulta corta por condición de ventana.
- Los totales suman filas de `guard_calls` en memoria de Python; con ventanas de 30 días y mucho tráfico por sujeto convendría una agregación en SQL.
- Las llamadas previas cuentan por haber sido permitidas, no por haberse ejecutado: una llamada permitida cuyo efecto nunca se reporta sigue sumando.
- Los registros antiguos sin `totals` se cargan con un mapa vacío.

## Pendiente

- Actualizar `docs/dominio/guard.md`, `docs/integracion.md` y el README (otro integrador).
- Texto propuesto para la tabla de condiciones de `docs/integracion.md`, tras la fila de `exceeds`:

  `| `window_exceeds` | el valor de esta llamada más la suma del mismo argumento en las llamadas permitidas previas del mismo sujeto y herramienta, dentro de `window_seconds` (60 a 2 592 000), supera `limit` | `amount` |`
