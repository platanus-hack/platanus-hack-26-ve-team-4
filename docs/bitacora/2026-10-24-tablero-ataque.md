---
fecha: 2026-10-24
autor: "@equipo-rojo"
rama: feat/tablero-ataque
pr: pendiente
estado: en revisión
dominios: [arena, attempts, llm, prober, frontend]
requisitos: []
---

# Tablero de ataque en vivo para la demo

## Qué cambió

- Backend: `GET /api/operator/live?sessions=N` (secreto de operador) en el módulo nuevo `agent_zero/live/`. Devuelve las N sesiones con actividad más reciente, con sus intentos, y cinco KPI con su `n` y su fuente. Enmascara las sesiones del público (`sess-…` sin prefijo `Agente-`) mientras la ronda no esté revelada: ruta `null` y `confirmed_violation`/`contained_honeypot` como `apparent_success`. Las KPI 2 y 3 cuentan solo enjambre y Prober hasta revelar.
- `llm/reporting.py`: `measured_tokens(records)`. Los tokens del atacante y del señuelo salen con `measured: false` y el rótulo «no medido en modo demo» cuando el ledger no tiene uso medido; nunca un 0.
- `backend/scripts/attack_swarm.py`: enjambre de 4 a 6 agentes simulados (`Agente-1…K`) que atacan en paralelo por la API pública con las plantillas de `prober/playbooks.py` y los mutadores de texto. No escribe textos de ataque nuevos.
- Frontend: ruta `/tablero` (`features/board/`) con seis chats, cinco KPI, casillas estables, fijar sesión y modo sin movimiento. El login de operador se extrajo a `OperatorGate`, compartido con `OperatorPage`; el mapa `OUTCOMES` de `AttemptList` se exporta y gana `apparent_success`.
- Documentación: `docs/dominio/tablero.md`, índice de dominios, `demo.md` y `frontend.md`.

## Por qué

Para la demo del domingo hace falta una visión de ataque: varios atacantes a la vez, mensaje a mensaje, con números que el jurado pueda verificar. La proyección usa revelación, así que antes de revelar el público no puede mostrar ruta ni violaciones sin arruinar el engaño.

## Archivos

- `backend/src/agent_zero/live/` (nuevo), `backend/src/agent_zero/llm/reporting.py`, `backend/src/agent_zero/main.py`
- `backend/scripts/attack_swarm.py`
- `frontend/src/features/board/`, `frontend/src/features/operator/OperatorGate.tsx`, `OperatorPage.tsx`, `AttemptList.tsx`, `frontend/src/app/App.tsx`
- Pruebas: `backend/tests/live/`, `frontend/src/features/board/BoardPage.test.tsx`

## Cómo se verificó

Desde `backend/` (contenedor Linux): `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` y `uv run pytest`. Desde `frontend/`: `pnpm biome check .`, `pnpm typecheck` y `pnpm test`. Prueba de punta a punta contra un backend en modo `demo`: cinco agentes del enjambre aparecen como cinco sesiones `swarm` con sus intentos y una campaña adaptativa del Prober aparece como sesiones `prober`. No hubo revisión visual en navegador.

## Riesgos y efectos en otros frentes

- El tipo de sesión se deduce del alias: un participante que elija `Agente-…` se ve como agente simulado sin enmascarar.
- Cada caso del Prober abre su propia sesión, así que una campaña ocupa varias casillas; fijar sesiones del enjambre evita que se desplacen.
- La plantilla de cambio de dirección (D-04) no existe en `main`; el enjambre la usará cuando `campaign_case` la incluya.
- El endpoint lee todos los intentos de la ronda en cada consulta (cada 1,5 s).
