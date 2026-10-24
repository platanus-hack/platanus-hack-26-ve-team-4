---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: fix/eventos-ids-sin-redaccion
pr: pendiente
estado: en revisión
dominios: [events, armor]
requisitos: [CORE-05]
---

# Los identificadores del servidor ya no se redactan en los eventos

## Qué cambió

`EventStore._redact_value` (`events/event_store.py`) pasaba por `ModelArmor.redact_pii` todos los textos de un evento antes de guardarlo, incluidos los identificadores. Ahora deja intacto un valor solo si cumple las dos condiciones:

- va en un campo de identificador (`id`, `*_id` o `*_ids`, también dentro de listas y diccionarios);
- tiene la forma exacta de un id creado por `shared.ids.new_id`: `prefijo-` más 12 caracteres hexadecimales (`SERVER_ID`).

Cualquier otro texto se sigue redactando, incluidos los campos de id que no tienen esa forma, como un `order_id` que propone el modelo.

## Por qué

La CI del PR #43 falló en `tests/arena/test_findings_and_patch_events.py::test_evaluation_and_finding_events_go_through_the_outbox` (Postgres). El `finding_id` público llegó como `finding-[PHONE]ffb` en vez de `finding-929410922ffb`:

- la parte hexadecimal `929410922` calza con el patrón de celular chileno de `armor/pii_patterns.py` (`9` y ocho dígitos);
- pasa con cerca del 1 % de los ids, por eso el fallo era intermitente;
- en el producto, rompía el vínculo entre el evento y su hallazgo, intento o sesión.

No se tocaron los patrones de `armor`: siguen redactando teléfonos en el texto libre.

## Archivos

- `backend/src/agent_zero/events/event_store.py`
- `backend/tests/events/test_event_redaction.py` (nuevo, CORE-05)
- `docs/trazabilidad.md` (fila CORE-05 de "Requisito -> tests")

## Cómo se verificó

En contenedor `python:3.12-slim-bookworm`:

- `ruff check`, `ruff format --check` y `mypy src tests`, sin errores;
- `tests/events`, `tests/test_traceability.py` y `tests/arena/test_findings_and_patch_events.py`: 15 pasan.

Se probó una mutación: sin la excepción de ids, falla `test_server_ids_survive_redaction_even_when_they_look_like_phones`.

## Riesgos

- Un texto con la forma exacta de un id dentro de un campo de id no se redacta. Si el modelo propone un valor así, queda tal cual; solo puede contener dígitos y letras de `a` a `f`.
