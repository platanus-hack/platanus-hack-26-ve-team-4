---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: feat/consola-pruebas
pr: pendiente
estado: en revisión
dominios: [arena, frontend]
requisitos: []
---

# Consola de pruebas: chat y auditoría en vivo en una pantalla

## Qué se hizo

- **Backend:** cada paso denegado de la auditoría trae etapa, motivo y detalle de Armor; cada intento, su familia; y el detalle del chat, `risk_score` y `risk_signals` (`arena/audit_signals.py`, aditivo).
- **Auditoría:** `Exchange` y `ToolStep` salen de `ChatAudit.tsx` como componentes compartidos; con el modo `live` añaden la clasificación y abren la traza.
- **Consola `/consola`:** `OperatorGate`, enlace «Consola», chat (`AttemptChat`) a la izquierda y auditoría en vivo a la derecha, con sondeo de 1,5 s; «Nueva sesión» y lista de sesiones anteriores.
- **Documentación:** `docs/dominio/frontend.md` y `docs/dominio/arena.md`, solo con lo implementado.

## Decisiones

- **Sesión propia de la consola** (`agent-zero:consola:v1`). No se reutilizó `openTestChat`, porque reemplaza la sesión del participante guardada en el navegador.
- **Backend aditivo:** los contratos existentes no cambian. Los campos nuevos salen de los eventos `tool_denied` y de `routing/session_risk`; `oracles/trace_reader.py` no se tocó.
- **Sin endpoint nuevo:** la auditoría en vivo reutiliza `GET /api/operator/audit/chats/{id}` con `usePolling`.

## Cómo se verificó

Comandos ejecutados sobre el árbol de `feat/consola-pruebas` después del paso 4. Este paso solo cambia documentación.

| Comprobación | Resultado |
| --- | --- |
| `ruff check .` (backend) | All checks passed! |
| `ruff format --check .` (backend) | 703 files already formatted |
| `mypy src tests scripts`, en Windows | 4 errores en `telemetry/audit_store.py` (`flock`, `LOCK_UN`); archivo que esta rama no modifica; su último cambio (`be2893b`) ya está en `main` |
| `mypy --platform linux src tests scripts` | Success: no issues found in 689 source files |
| `pytest -q tests/arena`, en `python:3.12-slim-bookworm` sin puertos | 98 passed in 353.75s |
| `pnpm exec biome check --vcs-root=.. .` (frontend) | Checked 137 files, sin correcciones pendientes |
| `pnpm typecheck` (`tsc -b`) | sin errores |
| `pnpm exec vitest run` de `consola`, `audit`, `monitor` y `app` | 7 archivos, 26 pruebas passed |
| `pnpm build` | build correcto; `index-nONBTEPt.js` 398.56 kB (gzip 125.41 kB) |

## Limitaciones

- Una sesión de una ronda archivada no se abre desde el selector: el enlace `/auditoria?chat=<id>` solo busca en la ronda en curso.
- No hubo revisión visual en navegador; las pruebas son de DOM (jsdom).
- `pytest` corrió solo `tests/arena`; la suite completa queda para la CI.
- `mypy` en Windows falla por `fcntl` en `telemetry/audit_store.py`; con `--platform linux` queda limpio.
