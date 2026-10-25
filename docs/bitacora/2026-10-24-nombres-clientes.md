---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: feat/nombres-clientes
pr: 34
estado: integrado
dominios: [victim, evals]
requisitos: [CORE-06]
---

# Nombre de los clientes en los pedidos de Yummi

## Qué cambió

Cada pedido de la víctima (Yummi, el bot de soporte del delivery) trae `customer_name`, obligatorio. Antes un cliente generado era solo `cust-demo-0046` con `cliente46@correo-demo.ve`, y el bot terminaba mostrando el ID.

| Cliente | Nombre | Correo |
|---|---|---|
| `cust-ana`, `cust-bruno`, `cust-carla` | Ana Rojas, Bruno Díaz, Carla Méndez | Sin cambios: `ana.rojas@correo-demo.ve`, etc. |
| `cust-demo-{n}` | `FIRST_NAMES[n % 20]` + `LAST_NAMES[n // 20 % 20]`. Determinista y sin aleatoriedad | `nombre.apellido{n}@correo-demo.ve`, en ASCII y con el número para que sea único |

Ejemplo: `cust-demo-0046` es **Pedro Pérez**, con `pedro.perez46@correo-demo.ve`. Las 20 × 20 combinaciones no se repiten hasta el número 400, así que los primeros 100 clientes tienen nombres distintos. Las listas no incluyen los nombres ni los apellidos de los tres clientes semilla.

En el señuelo, `honeypot_order()` cambia también el nombre y el correo por una identidad fabricada. Antes el señuelo conservaba el correo real del cliente. La identidad sale de `crc32(customer_id)` sobre listas de 10 × 10 nombres **disjuntas de las reales**, así que:

- nunca coincide con el nombre ni con el correo de ningún cliente del entorno protegido;
- es la misma en todos los pedidos de un cliente, porque depende del cliente y no del pedido.

Ejemplo: en el señuelo, Ana Rojas aparece como **Isabel Salazar** (`isabel.salazar@correo-demo.ve`) en sus dos pedidos.

Todos los nombres son ficticios: combinaciones comunes en Venezuela, sin personas reconocibles y sin teléfonos.

## Por qué

Un bot de soporte que saluda por el ID no es creíble en la demo, y un nombre es el dato personal que cualquiera reconoce si un ataque lo filtra. Que el señuelo use otra identidad, estable por cliente, mantiene coherente el mundo falso de una sesión desviada sin exponer datos del protegido.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/src/agent_zero/victim/schemas.py` | `Order` gana `customer_name` (obligatorio) |
| `backend/src/agent_zero/victim/customer_names.py` | Nuevo: listas de nombres reales y del señuelo, `demo_customer_name()`, `customer_email()` y `decoy_identity()`. Separado por el límite de unas 200 líneas de `fixtures.py` |
| `backend/src/agent_zero/victim/fixtures.py` | `SEEDED_CUSTOMER_NAMES` y el nombre y el correo de los `cust-demo-*` |
| `backend/src/agent_zero/victim/honeypot_fixtures.py` | El señuelo fabrica nombre y correo por cliente |
| `backend/tests/victim/test_customer_names.py` | Nuevo: nombres fijos, determinismo, unicidad en los primeros 100, correos únicos y reconocibles, listas disjuntas y `get_order` con `customer_name` |
| `backend/tests/victim/test_honeypot_orders.py` | El señuelo nunca repite un nombre ni un correo real (CORE-06) y su identidad es la misma en todos los pedidos de un cliente |
| `docs/dominio/victim.md`, `docs/dominio/traza-herramientas.md` | Campo nuevo del pedido, módulo nuevo y regla del señuelo |

La siembra (`environment_state.py`), `get_order` en la arena y en la flota, y `evals/suite.py` no cambian: usan el pedido completo con `model_dump()`. `llm/demo_model.py` arma la respuesta solo con `order_id` y `status`, así que no cambia. `docs/trazabilidad.md` no cambia: la prueba nueva de CORE-06 está en un archivo que ya era evidencia.

## Cómo se verificó

- En un contenedor `python:3.12-slim-bookworm`: `ruff check` y `ruff format --check` limpios (559 archivos), `mypy src tests scripts` sin errores (559 archivos) y `pytest` completo con 1078 passed y 2 skipped.
- En una corrida parcial, con `tests/victim tests/evals tests/decoy tests/test_traceability.py`, falló una vez `tests/evals/test_adaptive_campaign.py::test_closed_rounds_are_announced_publicly_with_counters_only` (`defender_did_not_close` en vez de `held_within_budget`). Aislada pasa, y en la suite completa también. `[SUPUESTO]` Es una prueba sensible al tiempo (espera de 120 s) y no tiene que ver con los nombres.
- Model Armor no bloquea ni redacta ninguno de los 503 nombres distintos (403 de los 500 clientes reales y los 100 posibles del señuelo), ni en `tool_output` ni en `model_output`. Sigue redactando el correo como `[EMAIL]`: el nombre queda visible.

## Riesgos y efectos en otros frentes

- **Contrato:** `victim/schemas.py:Order` gana un campo obligatorio. No tiene espejo en `frontend/src/features/*/types.ts`.
- **Evaluación:** `evals/suite.py:fixture_hash()` cambia; el nuevo es `0fe4044f383bdc0606fa07bd9983b52746232a8ce046ae72fb99abcf2d1aebf9`. No se editó `artifacts/`. Reanudar una evaluación guardada con los fixtures anteriores da `fixture_integrity_mismatch`, así que hay que regenerarla.
- **Señuelo:** el correo del señuelo ya no es el real. Nada lo comparaba, pero un oráculo futuro que busque el correo real en el señuelo ya no lo encontrará, y es lo esperado.
- **Bases sembradas:** la siembra es idempotente. Si la base ya tenía pedidos de antes de este cambio, hay que reiniciar la ronda para que tengan nombre.
- **Nombres repetidos sobre 400:** con la capacidad máxima de 500, `cust-demo-0404` a `cust-demo-0500` repiten los nombres de `cust-demo-0004` a `cust-demo-0100`. El correo sigue siendo único por el número.
- **PII visible:** Model Armor no detecta nombres. Un pedido ajeno filtrado muestra el nombre del cliente aunque el correo salga redactado.

## Pendiente

- Integrar este PR, con la revisión de @CarSanoja, porque toca `victim/`.
