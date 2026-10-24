# Arena: ronda, clasificación y operación

Estado: implementación revisada sobre la base funcional `1d0e21d`. El arranque común está en [núcleo](../nucleo.md); las pruebas transversales, en [guía de pruebas](../pruebas/README.md).

## Responsabilidad y archivos de entrada

`arena` ensambla los servicios del producto, publica el estado agregado y controla la vida de una ronda. Las decisiones de herramientas pertenecen al gateway y las de violación a los oráculos.

| Archivo | Función |
| --- | --- |
| [core.py](../../backend/src/agent_zero/arena/core.py) | Construye `ProductCore`, registra handlers y manifiestos, conecta gateway, workers, evaluación y recuperación. |
| [arena_service.py](../../backend/src/agent_zero/arena/arena_service.py) | Lee métricas y puntuación en un solo snapshot; cambia admisión/revelación. |
| [scoring.py](../../backend/src/agent_zero/arena/scoring.py) | Función pura de la clasificación: puntos, desempate y reconciliación al revelar. |
| [operator_router.py](../../backend/src/agent_zero/arena/operator_router.py) | Evidencia, repetición, reversión y controles de ronda. |
| [round_service.py](../../backend/src/agent_zero/arena/round_service.py) | Archivado, reset y recuperación de un reset interrumpido. |
| [round_snapshot.py](../../backend/src/agent_zero/arena/round_snapshot.py) | Define tablas de la ronda y el hash del snapshot. |
| [reset_router.py](../../backend/src/agent_zero/arena/reset_router.py) | Serializa mantenimiento y coordina la parada/reanudación de workers. |

## Estado persistido y contratos

| Tabla | Contenido |
| --- | --- |
| `arena_state` | Fila de control con `accepting` y `revealed`. |
| `arena_round_metadata` | `round_id`, inicio y primer ID de evento de la ronda actual. |
| `arena_round_archives` | Snapshot JSON, SHA-256, motivo, siguiente ronda y estado `resetting` o `completed`. |

| Ruta | Acceso y comportamiento |
| --- | --- |
| `GET /api/arena/state` | Pública: modo, ronda, inicio, cupo, conteos por estado/origen y `scores`. Tras revelar añade `confirmed_violations` y `contained_honeypot`. |
| `POST /api/operator/arena/pause` | Operador: cierra admisión; los intentos aceptados continúan. |
| `POST /api/operator/arena/resume` | Operador: abre una ronda no revelada ni en reset. |
| `POST /api/operator/arena/reveal` | Operador: exige drenaje de intentos, detiene nuevas generaciones de campañas y cierra la ronda. |
| `POST /api/operator/reset` | Operador: `{ "reason": "Nuevo ensayo" }`; archiva y devuelve estado nuevo más `archive_id`. Alias: `/api/operator/arena/reset`. |
| `GET /api/operator/rounds` | Operador: listado de archivos previos. |
| `GET /api/operator/rounds/{archive_id}/archive` | Operador: snapshot y hash, con verificación de integridad. |
| `GET /api/operator/monitor` | Operador: vista de la empresa ([monitor_view.py](../../backend/src/agent_zero/arena/monitor_view.py)). Por intento: resultado, ruta, familia (de la campaña o, si no hay, del analizador), hallazgo, parche que lo cerró (`version`, `activated_at`, `replay`), duración y uso de modelo (`calls`, `measured_calls`, tokens y coste) agregado desde el ledger LLM por `scope.attempt_id`. Más `totals` de los intentos de la ronda y `llm_mode`. |
| `GET /api/operator/attempts/{id}` | Operador: evidencia del intento con sus eventos y `graph`, el grafo de sus propias llamadas (efecto indebido según los veredictos, o denegación con su control). |

El operador usa `X-Operator-Secret`; un token Bearer de participante no concede estas operaciones. El estado público es un snapshot leído en una transacción. Los eventos recientes del navegador no son la fuente del marcador.

## Clasificación e invariantes

- Sólo `origin=audience` participa en la clasificación. El Prober y las repeticiones operativas se contabilizan como actividad autónoma.
- Durante la fase provisional se incluyen los objetivos aparentemente vulnerados en el señuelo. Al revelar, se excluyen los intentos `contained_honeypot` y cuentan las violaciones protegidas confirmadas.
- Cada participante recibe como máximo un punto por `(objective_id, policy_version)`. Reenviar o reconectar no añade puntos.
- El empate lo gana quien consiguió antes su primer punto de la fase visible: el primer éxito aparente antes de revelar y la primera violación confirmada después.
- Tras revelar, cada fila de `scores` reconcilia la provisional: `apparent` (puntos que parecían reales), `score` (confirmados) y `contained` (los que quedaron sólo en el señuelo). Quien sólo puntuó en el señuelo aparece con 0 puntos, para que la revelación muestre qué pasó con su éxito.
- `confirmed_violations` y `contained_honeypot` cuentan intentos con algún objetivo vulnerado, no puntos: repetir un ataque en el señuelo suma un intento contenido pero ningún punto.
- Una ronda revelada permanece cerrada: `resume` devuelve 409. La siguiente presentación requiere reset archivado.
- Las respuestas públicas no contienen la ruta, los canarios ni las trazas de operación. El propietario puede conocer su resultado real tras la revelación, pero las trazas siguen reservadas.

## Reset y recuperación

La ruta de reset toma `maintenance_lock`, espera la parada de los workers locales y después toma `admission_lock`. El servicio reserva el escritor de la base y rechaza intentos o runs del producto no terminales. Esto incluye campañas, validaciones, análisis y evaluación amplia; una cola visualmente vacía no basta.

Antes de borrar datos se persiste un archivo `resetting` y se cierra admisión. El snapshot incluye tablas del producto, runs/eventos/leases, eventos de la ronda, ambos entornos y auditoría. La memoria del snapshot de los entornos permanece cifrada. El hash se comprueba antes de completar o descargar el archivo.

Completar el reset restaura fixtures, política 0, participantes y metadatos. Los IDs de eventos siguen creciendo entre rondas. Se conservan archivos anteriores, registro de agentes, revocaciones, memoria de plataforma y runs ajenos al producto; el presupuesto/ledger LLM tampoco se reinicia. La eliminación de sesiones invalida sus tokens.

Si el proceso cae entre restablecer un entorno y confirmar la aplicación, `RoundService.initialize()` retoma el archivo pendiente antes de arrancar workers. Las operaciones de reset son repetibles. Las bases de aplicación y entornos no comparten una única transacción distribuida; el estado durable `resetting` permite cerrar esa ventana durante recuperación.

## Pruebas y evidencia

Desde la raíz, ejecutar en el entorno de desarrollo descrito en la [guía](../pruebas/README.md):

```bash
cd backend
uv run pytest tests/arena/test_round_reset.py tests/arena/test_core_cycle.py \
  tests/arena/test_control_concurrency.py -q
```

| Prueba | Garantía comprobada |
| --- | --- |
| [test_round_reset.py](../../backend/tests/arena/test_round_reset.py) | Archiva efectos/evidencia, invalida tokens, resembra, rechaza intentos en curso y recupera una caída entre entornos/aplicación. Incluye más de tres participantes y asignadores concurrentes. |
| [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py) | Resultado provisional, proyección privada/pública y permanencia en señuelo. |
| [test_control_concurrency.py](../../backend/tests/arena/test_control_concurrency.py) | Admisión concurrente frente a activación/reversión y eventos recuperables. |
| [ArenaPage.test.tsx](../../frontend/src/features/arena/ArenaPage.test.tsx) | Origen simulado visible, clasificación final con reconciliación y QR local. |
| [OperatorPage.test.tsx](../../frontend/src/features/operator/OperatorPage.test.tsx) | Autorización, exclusión de acciones y reset explícito con motivo. |

La verificación previa aprobó el ejercicio Docker y un ensayo LIVE con reset archivado. Son registros históricos enlazados desde [evidencias](../pruebas/evidencias.md); esta revisión documental no repite llamadas al proveedor.

## Límites y siguiente trabajo

La UI muestra el `archive_id` al resetear, pero todavía no lista `/operator/rounds` ni descarga snapshots de rondas: esas operaciones se hacen por API. Añadir esa navegación debe mantener la autorización y la verificación del hash.

El mantenimiento detiene workers locales; los demás procesos observan el estado durable y las reservas de escritura de la base. No sustituye un coordinador distribuido ni una prueba de carga. Para añadir una tabla del producto, revisar `ROUND_TABLES`, captura, borrado, recuperación y pruebas de reset en el mismo cambio. Para ampliar puntuación, modificar primero el cálculo del servidor y probar la fase provisional/final por separado.
