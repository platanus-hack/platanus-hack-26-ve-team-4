---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: integ/arena-buena-fe
pr: pendiente
estado: en revisión
dominios: [frontend, attempts, llm, agent-gateway, infraestructura]
requisitos: []
---

# Integración: buena fe, barra al salir y límite de 240 por minuto

## Qué cambió

La rama `integ/arena-buena-fe` sale de `origin/main` (`519a2f3`) y junta tres ramas con `git merge --no-ff`, en este orden:

| Orden | Rama | Merge | Bitácora |
|---|---|---|---|
| 1 | `feat/limite-240-por-minuto` | `60c57a2` | [límite de 240](2026-10-25-limite-240-por-minuto.md) |
| 2 | `feat/barra-al-salir` | `3ac635c` | [barra al salir](2026-10-25-barra-al-salir.md) |
| 3 | `feat/arena-buena-fe` | `02a0394` | [buena fe](2026-10-25-arena-buena-fe.md) |

Las tres ramas parten de `519a2f3`. Git mezcló `docs/dominio/tablero.md` solo, sin conflictos: la línea 138 (cupo de 240), la viñeta «Ruta y acceso» (147) y las franjas y la regla de buena fe (67, 160 y 161) quedaron con las tres ediciones.

`feat/chat-de-prueba` no entra en esta integración.

## Por qué

Fernando pidió resolver los pedidos en commits chicos y llevarlos juntos en un solo PR.

## Cómo se verificó

Desde el worktree `wt-integ-arena`, con las tres ramas ya mezcladas:

- `pnpm install --frozen-lockfile`: lockfile al día, 139 paquetes.
- `pnpm exec biome check --vcs-root=.. .`: 113 archivos, sin errores.
- `pnpm typecheck` (`tsc -b`): sin errores.
- `pnpm test` (Vitest): 30 archivos y 182 tests en verde. La base tenía 170; la barra suma 2 y la buena fe suma 10.
- `pnpm build`: 180 módulos, `index-6mgD0JLO.js` de 379,39 kB (gzip 119,58 kB).
- `uv run ruff check .`: All checks passed!; `uv run ruff format --check .`: 697 archivos ya formateados.
- En Docker `python:3.12-slim-bookworm`, con el entorno virtual en `/tmp/venv` del contenedor:
  - `pytest -q tests/arena tests/sessions tests/test_traceability.py`: 108 passed, 1 skipped, en 226,75 s.
  - `pytest -q tests/llm tests/agent_gateway tests/live`: 179 passed, 2 skipped, en 20,59 s.
  - `mypy src tests scripts`: Success: no issues found in 683 source files.
- `git log origin/main..HEAD --format=%B | grep -ci co-authored`: 0.

## Riesgos

- Los riesgos de cada rama siguen en su bitácora: sincronizar el Blueprint de Render y actualizar un `.env` local con `AGENT_ZERO_LLM_SESSION_CALL_LIMIT=40`.
- No hubo revisión visual en navegador. Las pruebas son de DOM.

## Pendiente

- Integrar `feat/chat-de-prueba` sobre esta rama, o sobre `main` cuando esta entre, y volver a correr su verificación.
- Revisión visual de las franjas, las burbujas y la barra al salir.
