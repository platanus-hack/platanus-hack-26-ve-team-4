---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: fix/senuelo-continuidad
pr: pendiente
estado: en revisión
dominios: [victim]
requisitos: [CORE-06]
---

# Continuidad del señuelo: los pedidos propios no cambian al desviar

## Qué cambió

Antes, la base del señuelo guardaba todos los pedidos fabricados con `honeypot_order()`, también los del cliente de la sesión. Al desviar, el participante veía cambiar sus propios datos. Ejemplo, `cust-demo-0032`:

| Base | Nombre | `D-32001` | `D-32002` |
|---|---|---|---|
| Protegida | Rafael Rodríguez | Smash Burger Co. · Bella Vista, destino en Tierra Negra, Maracaibo | Panadería La Espiga Dorada · 5 de Julio, mismo destino |
| Señuelo, antes | Elena Blanco | Comercio y destino de Valencia | Comercio y destino de Caracas |

Ahora:

1. **Pedidos propios.** En el señuelo, `get_order` de arena muestra los pedidos del cliente de la sesión con los mismos nombre, correo, comercio, origen, destino y artículos que en el protegido. Estado y total ya eran iguales. `victim/honeypot_view.py:session_order()` reconstruye esos campos (`FABRICATED_FIELDS`) desde los fixtures en código (`orders_for_customer`). El resto del registro sigue siendo del señuelo: el canario `AZH_*`, `refunded` y la operación guardada.
2. **Pedidos ajenos.** Siguen fabricados, pero coherentes. El destino fabricado depende del `customer_id` (`decoy_delivery_address()`), igual que el nombre y el correo, así que los dos pedidos de un cliente ajeno muestran la misma identidad y la misma dirección. Sus comercios son de la ciudad de ese destino: `HONEYPOT_ORDERS` pasó de 6 a 8 comercios, dos por ciudad (Caracas, Valencia, Carabobo y Maracaibo), y los pedidos consecutivos de un cliente alternan entre los dos. `DecoyOrder` ya no trae `delivery_address`.

Con el cambio, `cust-demo-0032` sigue siendo Rafael Rodríguez en su sesión desviada. Otra sesión que lea sus pedidos en el señuelo ve a Elena Blanco, con destino `Calle Réplica 46, Res. Ensayo, piso 8, Santa Rita, Maracaibo` en los dos pedidos: `D-32001` de Patacones del Lago · Santa Rita y `D-32002` de Locatel · La Lago.

## Por qué

Un participante desviado que vuelve a consultar su propio pedido y lo encuentra a nombre de otra persona, en otra ciudad, detecta el señuelo de inmediato. Mostrar sus datos tal como los conoce no expone nada nuevo: es lo que ese mismo cliente ya ve en el protegido.

## Aislamiento entre entornos

`docs/dominio/routing.md` exige que el señuelo use su propia base y su propia memoria, y `docs/dominio/victim.md` que `protected.db` y `honeypot.db` estén separadas. Se respeta así:

- `session_order()` no recibe ni abre ningún `Environment`: solo el registro del señuelo, el nombre del entorno y el `session_customer_id`. Los datos propios salen de `victim/fixtures.py`, que es código. Una prueba lo comprueba con solo una base del señuelo en memoria, sin base protegida.
- El dueño se toma del `CallContext` fijado por el servidor (`session_customer_id`), no de un argumento del modelo: ninguna sesión puede pedir la vista de dueño de un pedido ajeno.
- La base del señuelo sigue guardando todos los pedidos fabricados: siembra, `Environment.order()`, `orders()`, snapshot y reset no cambian.
- El canario sigue siendo el `AZH_*` del señuelo, así que la comprobación de fuga de `oracles/assessment_service.py` (canarios `AZP_` del protegido en la respuesta o en las salidas) no cambia.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/src/agent_zero/victim/honeypot_view.py` | Nuevo: `session_order()` |
| `backend/src/agent_zero/victim/honeypot_fixtures.py` | Ocho comercios señuelo, dos por ciudad; `DECOY_ZONES`, `decoy_delivery_address()`, `FABRICATED_FIELDS`, `city_of()`; `honeypot_order()` usa el destino del cliente y alterna comercios de su ciudad |
| `backend/src/agent_zero/victim/scenario_tools.py` | `get_order` pasa el pedido guardado por `session_order()` |
| `backend/tests/victim/test_honeypot_continuity.py` | Nuevo (CORE-06): pedido propio igual antes y después del desvío, pedido ajeno fabricado, dos pedidos de un cliente ajeno con la misma identidad y destino, canario `AZH_` y vista propia sin base protegida |
| `backend/tests/victim/test_honeypot_orders.py` | Destino del señuelo en la ciudad de sus comercios, el mismo en todos los pedidos de un cliente (CORE-06), y comercios distintos en sus pedidos |
| `backend/tests/victim/test_knowledge_isolation.py` | Los valores prohibidos en el índice incluyen los destinos fabricados de los 500 clientes |
| `docs/dominio/victim.md`, `docs/trazabilidad.md` | Módulo nuevo, regla de continuidad, prueba nueva en CORE-06 |

## Cómo se verificó

- En un contenedor `python:3.12-slim-bookworm`, con SQLite: `ruff check` y `ruff format --check` limpios (633 archivos), `mypy src tests` sin errores (616 archivos) y `pytest` completo con 1185 passed y 23 skipped.
- Con Postgres (`pgvector/pgvector:pg17`, `AGENT_ZERO_TEST_DATABASE_URL`): `tests/victim`, `tests/decoy`, `tests/arena/test_round_reset.py` y `tests/test_traceability.py` con 147 passed y 2 skipped.

## Riesgos y efectos en otros frentes

- **`refunded` no viaja:** si el cliente pidió un reembolso en el protegido antes del desvío, en el señuelo su pedido muestra el `refunded` del señuelo (0 si no hubo reembolso ahí). Copiarlo exigiría leer la base protegida.
- **Lectura cruda:** quien lea `Environment.order()` del señuelo, o su snapshot, ve el pedido fabricado también para el dueño. Solo `get_order` de arena aplica la vista de dueño. La herramienta original de la flota (`store_tools.py`) no usa entornos y no cambia.
- **Operaciones guardadas:** la tabla `operations` del señuelo guarda la salida de `get_order` del dueño, con sus datos de fixtures. Son datos de laboratorio del mismo cliente, no de la base protegida.
- **Bases sembradas:** la siembra es idempotente; una base del señuelo sembrada antes de este cambio conserva los destinos por pedido hasta reiniciar la ronda. La vista de dueño funciona igual sobre esa base.
- **Evaluación:** `evals/suite.py:fixture_hash()` solo usa `ORDERS`, `KNOWLEDGE` y el límite de reembolso, así que no cambia y una evaluación guardada se puede reanudar.

## Pendiente

- Integrar con la revisión de @CarSanoja, porque toca `victim/`.
- Cuando entre la herramienta para cambiar la dirección de entrega en el señuelo (decisión AGENT_ZERO-D-04), la vista de dueño tiene que respetar el destino cambiado en `honeypot.db` en vez de reponer el de los fixtures.
