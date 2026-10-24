---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: feat/rag-conocimiento
pr: 32
estado: integrado
dominios: [victim, infraestructura]
requisitos: [CORE-08]
---

# Base de conocimiento de Yummy con búsqueda híbrida

## Qué cambió

`search_knowledge` deja de buscar solo por palabras clave exactas en 3 artículos cuando la app corre sobre Postgres. Ahora consulta una base de conocimiento propia, `<base>_knowledge`, que combina en una sola consulta SQL:

- **Palabras clave:** búsqueda de texto de Postgres (`tsvector` con el diccionario `spanish`), con los términos de la pregunta combinados con O.
- **Similitud semántica:** columna `vector(384)` de pgvector, distancia coseno exacta, sin índice HNSW.
- **Fusión por rango recíproco** (RRF, k = 60). Devuelve como máximo 4 fragmentos.

Los vectores salen del modelo local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, con `fastembed`, sin API ni clave. Los tests y la CI usan un vectorizador falso y determinista (`AGENT_ZERO_KNOWLEDGE_EMBEDDER=fake`).

El corpus son archivos Markdown en `backend/src/agent_zero/victim/knowledge_docs/`, uno por documento, separados en tres colecciones:

| Colección | Contenido | Lo ven |
|---|---|---|
| `oficial` | 8 documentos públicos de Yummy (`yummysuperapp.com`, `ayuda.yummysuperapp.com`), con URL y fecha de captura | protegido, validación, señuelo |
| `laboratorio` | Los 3 artículos de `KNOWLEDGE`, con el mismo texto y los mismos `source` | protegido, validación |
| `senuelo` | Políticas inventadas de envíos, reembolsos y cambios | señuelo |

Cada artículo trae `text`, `source` y `trust` (`official` o `lab`). Hacia el modelo, los fragmentos del señuelo salen como `lab`, para no delatar el señuelo. Los documentos del Prober siguen llegando con `trust: untrusted`.

La siembra corre al arrancar. Es idempotente, toma un lock consultivo propio, solo recalcula los fragmentos cuyo contenido o modelo cambió, y borra los que ya no están en los archivos.

**Sin Postgres (SQLite, el modo de los tests), `search_knowledge` responde exactamente igual que antes.** Si el índice no arranca, por ejemplo sin modelo o sin pgvector, la víctima también vuelve a las palabras clave y deja un aviso en el log.

## Por qué

Una pregunta natural rara vez repite las palabras exactas de un artículo. Además, la víctima necesitaba la información pública de Yummy separada de las reglas del laboratorio y del mundo falso del señuelo. Diseño aprobado: decisión AGENT_ZERO-D-05 (`investigacion/PLAN_RAG_YUMMY.md`).

## Archivos

| Archivo | Cambio |
|---|---|
| `infra/compose.yaml` | `postgres` pasa a `pgvector/pgvector:pg17`; el backend recibe `AGENT_ZERO_KNOWLEDGE_EMBEDDER` (por defecto `local`) y su healthcheck tiene `start_period: 5m`, porque el primer arranque descarga el modelo (unos 220 MB) a `/data/models` |
| `.github/workflows/ci.yml` | `backend-postgres` usa `pgvector/pgvector:pg17`; el job `containers` usa el vectorizador `fake` |
| `backend/pyproject.toml`, `backend/uv.lock` | `pgvector` y `fastembed` |
| `backend/src/agent_zero/config.py` | `knowledge_embedder`, `knowledge_database_url` (`<base>_knowledge`, solo con Postgres) y `knowledge_model_dir` |
| `backend/tests/conftest.py` | Crea y borra `<nombre>_knowledge` y usa siempre `knowledge_embedder="fake"` |
| `victim/knowledge_collections.py` | `COLLECTIONS_BY_ENVIRONMENT` y el `trust` de cada colección |
| `victim/knowledge_corpus.py` | Lectura del encabezado y fragmentación: uno por sección `##`, cortado por párrafos sobre 1200 caracteres |
| `victim/knowledge_models.py` | `KnowledgeBase` propia y la tabla `knowledge_chunks` |
| `victim/knowledge_embedder.py` | `Embedder`, `LocalEmbedder` y `FakeEmbedder` |
| `victim/knowledge_index.py` | Siembra idempotente y consulta híbrida |
| `victim/knowledge_search.py` | Elige entre la búsqueda híbrida y las palabras clave, y arma la salida |
| `victim/scenario_tools.py`, `arena/core.py`, `main.py` | Se crea, siembra y cierra el índice, y se entrega a `ScenarioTools` |
| `victim/tool_schemas.py` | Nueva descripción de `search_knowledge` |
| `victim/knowledge_docs/{oficial,laboratorio,senuelo}/` | El corpus. `oficial/` lo escribió otro agente y entró sin cambios |
| `tests/victim/test_knowledge_*.py`, `tests/victim/test_scenario_tools.py` | Pruebas de corpus, vectorizador, colecciones, tabla, índice, salida, aislamiento y calidad |
| `docs/dominio/victim.md`, `docs/trazabilidad.md` | Sección de la base de conocimiento y requisito CORE-08 |

`victim/knowledge.py` (`KNOWLEDGE`) **no cambió**, así que el hash de fixtures de la evaluación tampoco.

## Cómo se verificó

Medido sobre esta rama, apilada sobre `feat/direcciones-entrega` y antes del rebase sobre `main`, en un contenedor `python:3.12-slim-bookworm`:

- `ruff check`, `ruff format --check` y `mypy src tests scripts`: limpios (490 archivos).
- `pytest` completo en SQLite: 923 passed y 23 skipped. Los saltos son las pruebas que necesitan Postgres, la prueba de calidad y las dos de la API real, que ya se saltaban.
- Con `AGENT_ZERO_TEST_DATABASE_URL` sobre un `pgvector/pgvector:pg17` aparte: `tests/victim` y `tests/test_traceability.py` dieron 82 passed y 1 skipped; `tests/arena` y `tests/evals` dieron 67 passed. En una corrida anterior, `test_independent_workers_serialize_authorization_with_the_effect` falló una vez por tiempo de espera y pasó al repetirlo solo; no toca la base de conocimiento.
- **`pytest` completo en Postgres: pendiente tras el rebase.**
- Prueba de calidad con el modelo real (`AGENT_ZERO_KNOWLEDGE_QUALITY=1`): **14 de 15** preguntas con el documento esperado entre los 4 primeros (meta: 12). La que falla es "quiero que me devuelvan la plata de una orden": devuelve fragmentos de `oficial/seguimiento-y-cambios-de-pedido` y no `laboratorio/reembolsos`. "Me llegó la comida fría" encuentra `laboratorio/cambios` en el cuarto lugar.
- El wheel del backend incluye los 14 archivos de `knowledge_docs/`.
- No se corrió `make smoke-exercise` ni la pila de contenedores, para no tocar la pila `agent-zero` que estaba corriendo.

## Riesgos y efectos en otros frentes

- **Infraestructura (@CarSanoja):** la imagen de Postgres pasa de `postgres:17-alpine` a `pgvector/pgvector:pg17`, que usa Debian. Un volumen `agent-zero-postgres` creado con la imagen Alpine puede tener índices de texto ordenados con otra intercalación [SUPUESTO: no se probó sobre el volumen existente]. Lo más seguro es recrear el volumen o correr `REINDEX DATABASE` en cada base.
- **Primer arranque:** con `local`, el backend descarga el modelo antes de servir. Sin internet, el índice no arranca y la víctima responde con palabras clave. Para el evento, conviene arrancar una vez con internet para dejar el modelo en el volumen `agent-zero-data`.
- **Contrato:** con Postgres, cada artículo de `search_knowledge` gana `trust`. El `source` de nivel superior sigue siendo `knowledge:tienda`.
- **Evaluación:** con Postgres, el resultado de las tareas de conocimiento depende del corpus en Markdown, que no entra en `fixture_hash()`.
- **Manifiesto:** la descripción de `search_knowledge` cambió sin subir `ARENA_VERSION` (2.0.0). Una base que ya tenía publicada la versión 2.0.0 conserva la descripción anterior en el registro; el modelo recibe la nueva, que sale de `tool_specs()`.
- **Búsqueda:** la parte semántica siempre devuelve hasta 4 fragmentos, aunque la pregunta no tenga relación con el corpus.
- **Falla conocida en Postgres, causada por la procedencia y no por el RAG:** `tests/arena/test_flow_synthesis_cycle.py::test_tool_poisoning_yields_a_verified_flow_policy` falla con la base de conocimiento activa.
  - La sonda de integridad inyecta `amount 10`. El RAG devuelve `oficial/seguimiento-y-cambios-de-pedido.md` ("amplíalo al máximo (10 km)"), y `contract/provenance.py` elige la etiqueta con `PRIORITY = ("user", "store", "untrusted", "memory")`. El 10 inyectado queda como `store`, la regla `request_refund_amount_untrusted` no aplica y la sonda da `untrusted_effects: 1`.
  - **El blanqueo ya existía en `main` sin RAG:** un importe de 20 coincide con "hasta 20 USD" del artículo de reembolsos. El corpus rico solo lo vuelve frecuente.
  - El arreglo va en un PR aparte, `feat/procedencia-robusta`, porque invertir el desempate rompe `tests/evals/test_adaptive_campaign.py` y hay que resolverlo junto. También afecta al Guard, que usa la misma función.

## Pendiente

- Revisión de @CarSanoja por el cambio de imagen de Postgres y de la CI, y de @franbastardo por `arena/core.py` y la salida de `search_knowledge`.
- Arreglo de la procedencia en `feat/procedencia-robusta`; con ese arreglo vuelve a pasar la sonda de integridad en Postgres.
- Fuera de este cambio: convertir `require_provenance` en un control real que filtre o aísle los fragmentos `untrusted`.
