---
fecha: 2026-10-24
autor: "@equipo-rojo"
rama: feat/tablero-ataque
pr: pendiente
estado: en revisión
dominios: [arena, attempts, llm, prober, sessions, frontend]
requisitos: []
---

# Tablero de ataque en vivo para la demo, convertido en la Arena en vivo

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

- La plantilla de cambio de dirección (D-04) no existe en `main`; el enjambre la usará cuando `campaign_case` la incluya.
- El endpoint lee todos los intentos de la ronda en cada consulta (cada 1,5 s).

## Segunda iteración: Arena en vivo en `/arena`

### Qué cambió

- **`GET /api/operator/live` v2.**
  - Cada intento trae número, versión de política, negaciones (`tool_denied` con visibilidad `operator`, sin argumentos), objetivos violados, el parche que lo cubrió (`patched_by`) y la técnica del caso del Prober.
  - El Público sin revelar viaja sin desenlace, ruta, respuesta ni negaciones, con `concealed: true`.
  - El Prober se agrupa en una sesión por campaña.
  - Las KPI cuentan solo intentos terminados (`in_flight` aparte) con la misma base de alcance. «Espacio seguro» cuenta sesiones en señuelo con al menos un intento contenido, y «Parches» ignora las políticas revertidas y los hallazgos del Público sin revelar.
  - Se agregan `accepting` y `sessions_total`.
- **Prefijo reservado.** `POST /api/sessions` reserva el prefijo `Agente-` para quien envía el secreto de operador (409 sin él, 401 si es incorrecto). `attack_swarm.py` lee el secreto de `AGENT_ZERO_OPERATOR_SECRET` y lo envía solo al crear la sesión. El tablero ya no depende de una heurística que el público pueda falsear.
- **Frontend.** `/arena` pasa a ser la Arena en vivo de la maqueta aprobada, detrás de `OperatorGate`:
  - Escenario de 1920 × 1080 y cabecera con QR, «Cerrar acceso» (pausa y reanuda la ronda) y «Salir».
  - Carrusel de 8 chats con 3 a la vista y hasta 2 fijados.
  - Chats con los mapas `OUTCOME` y `DENIAL`, y cinco KPI.
- **Limpieza.** Se eliminaron la arena pública anterior (`ArenaPage`, co-evolución, clasificación, `useArenaEvents`) y la ruta `/tablero`. El backend público no cambió.

### Cómo se verificó

- **Backend**, en el contenedor `az-dev-tablero`: `ruff check`, `ruff format --check`, `mypy src` y `pytest` completo.
- **Frontend**: `biome check`, `typecheck`, `vitest` y `build`.
- **Revisión visual**: una captura a 1920 × 1080 con un navegador sin ventana y datos simulados, antes y después de revelar. Sirvió para ajustar la separación de la cabecera y el recorte de las negaciones.
- **Pendiente**: la prueba de punta a punta contra el stack.

### Riesgos

- Tras revelar no se puede reabrir la ronda: la pantalla lo dice («Ronda revelada») y quita el botón.
- El agregado lee todos los intentos en cada consulta (cada 1,5 s), más una consulta de eventos y una de casos de campaña por petición.
