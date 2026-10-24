---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: feat/procedencia-robusta
pr: pendiente
estado: en revisión
dominios: [contract, guard, victim]
requisitos: []
---

# La procedencia no blanquea un valor inyectado que también aparece en un texto confiable

## Qué cambió

En `backend/src/agent_zero/contract/provenance.py`, el desempate entre segmentos pasa de `("user", "store", "untrusted", "memory")` a `("user", "untrusted", "memory", "store")`. Es una sola línea, con un comentario. Si el valor de un argumento aparece en un segmento `untrusted` o `memory`, conserva esa etiqueta aunque también esté en uno `store`. Lo que escribe el usuario sigue ganando. Un valor que solo está en la tienda sigue siendo `store`.

Como `victim/provenance.py` y `guard/check_service.py` usan esa misma función, el arreglo cubre a la vez la víctima de la arena y el Guard de terceros.

## Por qué

**El hallazgo.** La procedencia se asigna buscando el valor de cada argumento en los textos de la conversación. Con la prioridad anterior, si un valor aparecía en un texto no confiable y también en uno confiable, ganaba el confiable. Así, un argumento inyectado quedaba blanqueado como `store`, y las reglas `*_untrusted` dejaban de aplicarse. Hay dos formas de que pase:

- **Coincidencia por azar en un texto de conocimiento.** Un monto inyectado coincide con un número igual de un artículo oficial, por ejemplo un tope en USD o una distancia en km. Con la base de conocimiento híbrida (PR #32) los fragmentos devueltos son más y más variados, así que esto pasa más a menudo. En `main` ya pasaba con un monto igual al tope del artículo de reembolsos.
- **El eco de una herramienta.** Una inyección pide consultar un pedido. `get_order` devuelve ese mismo `order_id` en su salida, y esa salida es `store`. Desde ese momento, el identificador inyectado parecía venir de la tienda. Esto se observó en la campaña adaptativa (abajo).

**El Guard estaba afectado.** En `main`, `POST /api/guard/{id}/check` con un contexto que trae el mismo monto en un segmento `store` y en uno `untrusted` devolvía `provenance.monto == "store"`. Por eso, la regla aprendida `*_untrusted` no frenaba una transferencia inyectada pequeña. Lo fija `tests/guard/test_router.py::test_a_store_copy_of_an_injected_value_does_not_launder_it`, que falla en `main` (`'store' == 'untrusted'`) y pasa con el arreglo.

**Por qué este arreglo y no otro.** Se evaluaron tres ideas:

- *Que `store` gane si el valor viene de la salida estructurada de una herramienta.* Se descartó porque es justo el caso del eco: `get_order` devuelve el `order_id` que la inyección le pidió consultar, y esa excepción lo volvería a blanquear.
- *Comparar números con más contexto, por ejemplo con unidad o frontera de palabra.* `contains` ya compara números como token completo (`250` no casa con `25`). Exigir la unidad no cierra el eco y agrega reglas frágiles. Con la nueva prioridad, una coincidencia por azar ya no blanquea nada.
- *Una etiqueta propia `knowledge` para los fragmentos de `search_knowledge`.* Cambiaría `Origin`, `ORIGINS`, el contrato YAML y el render de políticas, y no cubre el eco de `get_order`.

La inversión de prioridad cubre los dos casos con el menor cambio. El costo es conocido: si un valor legítimo de la tienda coincide por azar con un texto no confiable de la misma conversación, queda de baja integridad y la llamada se bloquea. El error queda del lado seguro.

## La regresión que se le atribuía al parche candidato

Un parche anterior con este mismo cambio (`wt-procedencia-candidato.patch`) se descartó porque `tests/evals/test_adaptive_campaign.py::test_closed_rounds_are_announced_publicly_with_counters_only` terminaba con `stop_reason == 'defender_did_not_close'`. Se investigó registrando, durante la prueba, cada argumento cuyo valor aparecía a la vez en `store` y en un segmento de baja integridad sin estar en `user`. Son los únicos casos en que la prioridad nueva y la vieja dan etiquetas distintas.

- **En la corrida que reprodujo el fallo, no hubo ningún caso.** Las etiquetas fueron idénticas a las de `main`, así que ese fallo no lo pudo causar el cambio de prioridad.
- **En tres corridas más del archivo con el cambio**, apareció un solo caso, en un intento de ataque. Era un `order_id` ajeno, pedido por una guía de envío no confiable y devuelto después por `get_order`. Con la prioridad vieja quedaba `store` (blanqueado). Con la nueva queda `untrusted`. No se vio ningún caso legítimo afectado, así que la hipótesis de un caso de validación etiquetado como `untrusted` no se confirmó.
- **La prueba ya es inestable en `main`.** Se corrió sola seis veces, alternando las dos prioridades en el mismo contenedor: `main` pasó 2 de 3 y el arreglo pasó 2 de 3. Las corridas que fallan terminan antes (unos 20 s, contra 35 a 55 s de las que pasan) con el mismo `defender_did_not_close`. Además, `main` sin cambios falló una de dos corridas del archivo completo en otra prueba (`test_adaptive_campaign_breaks_v0_then_holds_after_a_patch_with_exact_counts`).

La regresión del candidato era esa inestabilidad preexistente, no un efecto de la procedencia. No se investigó por qué la campaña a veces cierra con `defender_did_not_close` tan rápido: `prober/adaptive_planner.py` solo devuelve ese motivo cuando pasaron más de `prober_round_close_wait_seconds` (90 s) desde la última actualización de la ronda. [SUPUESTO] Puede haber una marca de tiempo vieja o una comparación de relojes que no corresponde.

## Archivos

| Archivo | Cambio |
| --- | --- |
| `backend/src/agent_zero/contract/provenance.py` | `PRIORITY` invertida para la baja integridad, con comentario |
| `backend/tests/contract/test_provenance.py` | Una copia confiable no blanquea `untrusted` ni `memory`; un valor solo de la tienda sigue `store` |
| `backend/tests/victim/test_provenance.py` | Un artículo oficial con el mismo número no blanquea el monto inyectado; los valores de `get_order` y de artículos oficiales siguen `store` |
| `backend/tests/guard/test_router.py` | El Guard: el monto y el destino inyectados quedan `untrusted` y se bloquean aunque un segmento `store` los repita; la misma llamada sin texto no confiable pasa |
| `docs/dominio/guard.md` | Desempate de la procedencia e invariante nuevo |

No se tocaron `policies/flow/`, `patches/`, `KNOWLEDGE`, el corpus ni las pruebas existentes.

## Cómo se verificó

En Docker (`python:3.12-slim-bookworm`, `uv sync --frozen`), en el commit `4c3f28f`:

- `ruff check`, `ruff format --check` y `mypy src tests scripts` (594 archivos) sin errores.
- Las tres pruebas nuevas que fijan el hallazgo **fallan en `main`** (`b9ba02a`) y pasan con el arreglo.
- `tests/victim tests/contract tests/guard tests/evals tests/arena` en SQLite: **186 pasan**.
- `tests/arena tests/evals` en Postgres (`pgvector/pgvector:pg17`): 98 pasan y 1 falla, `test_adaptive_campaign_breaks_v0_then_holds_after_a_patch_with_exact_counts`, la misma prueba inestable de `main`. Corrida sola, pasa. `test_tool_poisoning_yields_a_verified_flow_policy` y `test_round_curve` pasan.
- La suite completa en SQLite: 1115 pasan, 2 se omiten y 2 fallan. `test_closed_rounds_are_announced_publicly_with_counters_only` es la prueba inestable de arriba. `tests/decoy/test_decoy_flow.py::test_diverted_session_takes_the_bait_reuses_the_token_and_sees_its_card` pasa sola, y ni `decoy/` ni sus pruebas usan la procedencia.
- No se probó sobre la rama del RAG (PR #32).

## Riesgos y efectos en otros frentes

- **@CarSanoja (`contract/`, `victim/provenance.py`):** el cambio es una línea en su código. `victim/provenance.py` no cambió.
- **Falsos positivos:** un valor de la tienda que también aparece en un texto no confiable de la misma conversación ahora se bloquea. Con el corpus actual no se observó en las pruebas legítimas.
- **PR #32 (RAG):** al integrarse sobre esta rama, `test_tool_poisoning_yields_a_verified_flow_policy` en Postgres ya no debería necesitar el cambio que traía su propia entrada.

## Pendiente

- Investigar por qué la campaña adaptativa cierra a veces con `defender_did_not_close` en unos 20 s, en `main` y con el arreglo.
- Correr `test_tool_poisoning_yields_a_verified_flow_policy` en Postgres sobre la rama del RAG con este cambio.
