---
fecha: 2026-10-24
autor: "@FernandoSiavato"
rama: test/arena-autorizacion-cola-pausa
pr: pendiente
estado: en revisión
dominios: [attempts, arena, guard, frontend]
requisitos: [CORE-01, CORE-05]
---

# Tests de autorización de operador, límites de envío y pausa en vuelo, y `Retry-After` en los 429

## Qué cambió

- Los 429 de `POST /api/attempts` envían ahora `Retry-After` en segundos enteros:
  - Por frecuencia (12 intentos por minuto en ventana deslizante): el tiempo hasta que sale de la ventana el intento que deja a la sesión bajo el límite. Con la sesión justo en el límite es el intento más antiguo de la ventana. Mínimo 1 s.
  - Con la cola llena (un intento pendiente por sesión o 40 por origen): 5 s fijos (`QUEUE_RETRY_SECONDS`). La cola se libera cuando termina un intento pendiente, así que no hay una hora conocida de antemano; un intento suele tardar unos segundos [SUPUESTO: no se midió con el proveedor real], y 5 s es el mismo valor que la interfaz ya usaba cuando faltaba la cabecera.
- `AttemptRepository.recent_count` pasa a ser `created_since`, que devuelve las fechas de creación de la ventana en orden, para calcular ese tiempo. Los límites no cambian (siguen en `config.py`: 12 por minuto, 1 pendiente por sesión, cola de 40).
- Tests nuevos de backend:
  - `tests/arena/test_operator_authorization.py` (issue #4): un token Bearer de participante recién emitido y válido recibe 401 en la lectura de operación (intento con evidencia, intentos, políticas, hallazgos, rondas), en la reversión de política, en pausa, reanudación y revelación, en los dos reinicios y en la repetición; y en la activación y reversión de una política propuesta del Guard. El estado (ronda, admisión, revelación, versión activa, políticas, intentos, archivos de ronda, política propuesta) no cambia y el token sigue siendo válido después.
  - `tests/arena/test_attempt_limits.py` (issue #6): 4000 caracteres se aceptan y 4001 dan 422, en `message` y en `messages`; un segundo intento con otro pendiente de la misma sesión da 429 con `Retry-After: 5` y no afecta a otra sesión; la cola de la ronda llena da 429 con `Retry-After: 5`; el límite por minuto da 429 con el reloj inyectado (12 envíos cada 4 s, `Retry-After` 10, 1 y 1 a los 50 s, 59,5 s y 60 s, se acepta a los 60,001 s y el siguiente da 4).
  - `tests/arena/test_pause_in_flight.py` (issue #15): con un intento ya en `running` (un paso del worker), pausar no lo corta: termina `evaluated`, conserva al comienzo los mismos eventos que tenía y suma `attempt_evaluated`; los envíos nuevos de cualquier sesión dan 409 y no se crea ningún intento más.
- Frontend: el test de `AttemptChat` que decía cubrir `Retry-After` aceptaba cualquier número de segundos, así que pasaba también si se ignoraba la cabecera. Ahora exige 60 s con `Retry-After: 60` y hay un caso nuevo de 5 s cuando falta la cabecera. `AttemptChat.tsx` y `http.ts` no cambian: leen la cabecera bien.

## Por qué

Una auditoría encontró que el código cumplía los issues #4, #6 y #15, pero faltaban tests que lo fijaran: el único test de autorización usaba un token ya invalidado, no había test del largo máximo del mensaje ni de los dos 429, y la pausa solo probaba el 409. Además, la interfaz espera `Retry-After` y el backend no lo enviaba, así que siempre esperaba 5 s.

El issue #6 pide "1 intento cada 3 s"; ese límite no se tocó porque lo decide el equipo aparte.

## Archivos

- `backend/src/agent_zero/attempts/attempt_submission_service.py`, `repository.py`
- `backend/tests/arena/test_operator_authorization.py`, `test_attempt_limits.py`, `test_pause_in_flight.py` (nuevos)
- `frontend/src/features/participant/AttemptChat.test.tsx`
- `docs/trazabilidad.md` (tabla requisito → tests de CORE-01 y CORE-05), `docs/dominio/attempts.md`

## Cómo se verificó

Backend en contenedor `python:3.12-slim-bookworm` con `uv` 0.12.7, desde `backend/`: `uv run ruff check` (sin hallazgos), `uv run ruff format --check` (636 archivos ya formateados), `uv run mypy src tests scripts` (sin problemas en 622 archivos) y `uv run pytest -q` (1192 pasadas, 23 omitidas, 642,72 s). Todo offline, con SQLite.

Cada test nuevo se comprobó rompiendo a propósito el comportamiento que cubre, corriendo el test y restaurando el archivo (los respaldos se compararon byte a byte al terminar):

| Cambio temporal | Test que falló | Dónde falló |
| --- | --- | --- |
| `require_operator` deja pasar cualquier pedido | los dos de `test_operator_authorization.py` | la lectura de evidencia devuelve 200; la activación del Guard devuelve 200 |
| `max_length=4001` | largo del mensaje | los 4001 caracteres dan `[202, 429]` en vez de `[422, 422]` |
| `max_length=3999` | largo del mensaje | los 4000 caracteres dan 422 |
| sin el límite por minuto | límite por minuto | el envío 13 se acepta (202) |
| `Retry-After` fijo de 5 s en el límite por minuto | límite por minuto | `'5' == '10'` |
| sin `Retry-After` en el límite por minuto | límite por minuto | falta la cabecera (`KeyError`) |
| sin el límite de un pendiente por sesión | pendiente por sesión | el segundo envío da 202 |
| sin el límite de la cola de la ronda | cola llena | el segundo envío da 202 |
| sin `Retry-After` en la cola llena | pendiente por sesión y cola llena | falta la cabecera (`KeyError`) |
| la admisión ignora la pausa | pausa en vuelo | la sesión sin pendientes obtiene 202 en vez de 409 |
| pausar cancela los runs en vuelo | pausa en vuelo | el intento termina `inconclusive` en vez de `evaluated` |
| pausar borra el evento `attempt_queued` de los intentos en vuelo | pausa en vuelo | los eventos del final ya no empiezan por los registrados antes de pausar |

Frontend en contenedor `node:22` con pnpm 10.28.2 (corepack), desde `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint` (Biome, 76 archivos, sin cambios), `pnpm typecheck` (`tsc -b`, sin errores) y `pnpm test` (20 archivos, 93 tests pasados). pnpm avisa que el proyecto pide Node ≥ 24. Con `cause.retryAfterMs ?? 5000` cambiado a `5000` en `AttemptChat.tsx`, falla "respeta Retry-After sin regenerar la clave" y pasa el caso sin cabecera; se restauró el archivo.

## Riesgos y efectos en otros frentes

- `created_since` trae las fechas de la ventana de un minuto en lugar de un conteo; como mucho son tantas filas como el límite más uno.
- El test de frecuencia sube a 50 el límite de pendientes por sesión de su app para que los intentos encolados no oculten el límite por minuto, y sustituye `core.submissions` por un servicio con el reloj inyectado. El límite por minuto se prueba con su valor por defecto.

## Pendiente

- Decidir si el límite pasa a "1 intento cada 3 s" como pide el issue #6.
