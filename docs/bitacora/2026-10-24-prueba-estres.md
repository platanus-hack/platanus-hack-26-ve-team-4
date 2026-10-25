---
fecha: 2026-10-24
autor: "@CarSanoja"
rama: main
pr: ninguno  # push directo a main
estado: integrado
dominios: [sessions, runtime, telemetry, events, loadtest, infra]
requisitos: [RUN-01, OBS-02]
---

# Prueba de estrés con 100 participantes y cruce con la misión

## Qué cambió

- `backend/src/agent_zero/loadtest/`: generador de carga de la arena y del Guard.
  - Simula participantes honestos, participantes mixtos y una ola de repetición tras el parche.
  - El informe da carga, misión y Guard.
- `sessions/dependencies.py`: `current_session` usa su propia sesión de base de datos y la cierra antes del handler.
- `shared/database.py`, `config.py` y `main.py`: añaden `database_pool_size` (10) y `database_max_overflow` (20) para la base principal en Postgres.
- `runtime/run_worker.py` y `runtime/repository.py`:
  - el worker rellena cada hueco en cuanto se libera;
  - `runtime_priority_handlers` adelanta `validate_patch` y `finding_analysis` en la cola.
- `telemetry/audit_log.py` y `telemetry/audit_store.py`:
  - `append` verifica solo las líneas nuevas;
  - `entries()` analiza solo las nuevas;
  - el archivo se reutiliza mientras su inodo, tamaño y `mtime` no cambien.
- `events/audited_events.py`: índice incremental de eventos ya auditados para `deliver_pending`.
- `infra/production.env.example` y `docs/despliegue.md`: 8 workers, cola de 120 y pool 10 + 20.
- `docs/pruebas/estres-2026-10-24.md`: resultados y cruce con la misión.

## Por qué

Con 100 participantes la arena se caía. Primero se agotó el pool de conexiones. Corregido eso, el `py-spy` mostró que la auditoría reverificaba y releía toda la cadena en cada entrada. Era un coste cuadrático que dejaba la latencia en 48 s y el parche en 164 s.

## Archivos

- `backend/src/agent_zero/loadtest/*` y `backend/tests/loadtest/*`.
- `backend/src/agent_zero/sessions/dependencies.py` y `backend/tests/sessions/test_dependencies.py`.
- `backend/src/agent_zero/shared/database.py`, `backend/src/agent_zero/config.py` y `backend/src/agent_zero/main.py`.
- `backend/src/agent_zero/runtime/run_worker.py`, `backend/src/agent_zero/runtime/repository.py`, `backend/tests/runtime/test_run_worker.py` y `backend/tests/runtime/test_repository.py`.
- `backend/src/agent_zero/telemetry/audit_log.py`, `backend/src/agent_zero/telemetry/audit_store.py`, `backend/src/agent_zero/telemetry/audit_verifier.py`, `backend/tests/telemetry/test_audit_log.py` y `backend/tests/telemetry/test_audit_store.py`.
- `backend/src/agent_zero/events/audited_events.py`, `backend/src/agent_zero/events/event_delivery.py` y `backend/tests/events/test_audited_events.py`.
- `infra/production.env.example`, `docs/despliegue.md` y `docs/pruebas/estres-2026-10-24.md`.

## Cómo se verificó

- **Suite del backend:** 1240 aprobadas y 24 omitidas, con ruff y mypy estricto limpios.
- **Regresión del pool:** la prueba con Postgres y pool de 1 conexión falla con el código anterior (timeout del pool) y pasa con el arreglo.
- **Estrés DEMO con la pila Docker completa:**
  - 300/300 intentos y 90/90 repeticiones, sin errores ni timeouts.
  - 332 intentos/min y p50 de 16.6 s.
  - Parche activo en 48.8 s.
  - 14 violaciones confirmadas en v0 y 0 en v1.
  - 0 falsos bloqueos.
  - Guard: 1000/1000 correctos con p95 de 93 ms.
- **Estrés LIVE con `claude-haiku-5-5`:**
  - 80/80 intentos y 247 llamadas reales.
  - US$0.038319, con un tope de US$1.
  - 19 violaciones confirmadas en v0 y 0 en v1.
  - Parche activo en 36.1 s.

## Riesgos y efectos en otros frentes

- **Fingerprint del archivo de auditoría:** la caché de líneas confía en el inodo, el tamaño y el `mtime_ns`. Una edición que restaure exactamente los tres no se detectaría al añadir; sí la detecta `verify()` [SUPUESTO: `verify()` se ejecuta periódicamente desde el panel].
- **Prioridad de la validación:** puede retrasar intentos del público mientras se valida un parche.
- **Pools de conexiones:** cuatro engines de Postgres suman hasta 75 conexiones, por debajo de las 100 que trae Postgres por defecto.

## Pendiente

- La meta de 30 s para activar el parche: hoy son 36-49 s.
- Probar en la VM pública con TLS y con navegadores reales conectados por SSE.
- La arena sigue en un solo proceso de backend. Escalar a más núcleos exige sacar del proceso el broker de eventos y el `admission_lock`.
