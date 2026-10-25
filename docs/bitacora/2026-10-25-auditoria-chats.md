---
fecha: 2026-10-25
autor: "@franbastardo"
rama: feat/auditoria-chats
pr: 55
estado: integrado
dominios: [arena, frontend]
requisitos: []
---

# Auditoría de chats: entrar a cualquier chat y revisar todo su historial

## Qué cambió

- **Ruta nueva `/auditoria`** (secreto de operador, enlace «Auditoría» en el menú). Tiene tres partes:
  - **Selector de ronda:** la ronda en curso o cualquier ronda archivada completa.
  - **Lista de chats:** todas las sesiones con búsqueda por alias, sesión, cliente o mensaje, y filtros por tipo (público, enjambre, Prober, pruebas internas), violación y desvío.
  - **Historial del chat elegido.** Cada mensaje trae:
    - las burbujas tal como las vio el participante;
    - resultado, ruta, política y duración;
    - los objetivos vulnerados con su detalle;
    - una traza plegable con cada llamada a herramienta: propuesta, denegada con su control o ejecutada con su efecto, más argumentos, procedencia y salida.
- **Organización del historial:** se agrupa en conversaciones según `attempt_links` (las de «Nueva conversación»). Antes del primer mensaje atendido en el señuelo aparece el aviso del desvío con su motivo (filtro de entrada, violación confirmada o puntuación de riesgo).
- **Enlaces directos:** la ronda y el chat viven en la URL (`/auditoria?ronda=<archivo>&chat=<sesión>`), así que un enlace lleva directo a la conversación auditada.
- **Backend nuevo** (`arena/audit_view.py`, `arena/audit_router.py`):
  - `GET /api/operator/audit/rounds`;
  - `GET /api/operator/audit/chats?round=`;
  - `GET /api/operator/audit/chats/{session_id}?round=`.
- **Una sola lógica para ambas rondas:** la vista trabaja sobre filas planas, las mismas que guarda `round_snapshot`. La ronda en curso se consulta en la base y una ronda archivada se lee de su `snapshot`, tras comprobar el hash con `RoundService.archive`.
- `OperatorGate` acepta `intro`, un encabezado que se muestra solo mientras pide el secreto.

## Por qué

- El monitor muestra intentos sueltos y la Arena en vivo solo las sesiones más recientes.
- Faltaba poder abrir cualquier chat ya creado, incluso de una ronda reiniciada, y leerlo completo: qué escribió la persona, qué respondió Yummy, qué herramientas pidió, qué control las detuvo y en qué momento la sesión pasó al señuelo.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/src/agent_zero/arena/audit_view.py` | Nuevo: `session_kind` (incluye repeticiones del operador), `conversations`, `chat_index`, `chat_detail`, `audit_attempt` |
| `backend/src/agent_zero/arena/audit_router.py` | Nuevo: rondas, chats e historial; lectura de la ronda en curso o del archivo |
| `backend/src/agent_zero/main.py` | Registra `audit_router` |
| `backend/tests/arena/test_audit_router.py` | Nuevo: secreto requerido; conversaciones, traza, veredicto, desvío y respuesta sin canarios; ronda archivada y archivo inexistente (404) |
| `frontend/src/features/audit/` | Nuevo: `AuditPage`, `ChatList`, `ChatAudit`, `labels`, `types`, `audit.css` y `AuditPage.test.tsx` |
| `frontend/src/app/App.tsx` | Ruta `/auditoria` y enlace en el menú |
| `frontend/src/features/operator/OperatorGate.tsx` | Prop `intro` |
| `docs/dominio/arena.md`, `docs/dominio/frontend.md` | Contratos de los endpoints y comportamiento de la vista |

## Cómo se verificó

- Backend:
  - `tests/arena/test_audit_router.py`: 3 passed;
  - `ruff check`, `ruff format` y `mypy src tests` limpios (681 archivos);
  - suite completa: CI del PR #55 (backend y backend-postgres).
- Frontend: `pnpm lint`, `pnpm typecheck`, `pnpm test` (187 pruebas, 34 archivos, tras rebasar sobre `main`) y `pnpm build` en verde.
- Falta la revisión visual en navegador [SUPUESTO: solo se comprobó el DOM con jsdom].

## Riesgos y efectos en otros frentes

- **Costo por consulta:** la lista lee todas las sesiones e intentos de la ronda en cada consulta, cada 5 s mientras la vista está abierta. Una ronda archivada carga su `snapshot` completo, que no cambia, en cada consulta, y la vista la pide una sola vez.
- **Datos sensibles:** la traza muestra argumentos y salidas de herramientas, incluidos los valores sembrados del señuelo y de los canarios. Es solo para operador. La respuesta del asistente sí se muestra redactada, como la vio el participante.
- **Uso de modelo:** la auditoría no muestra tokens. El ledger LLM no forma parte del archivo de la ronda.

## Pendiente

- Exportar un chat auditado (JSON o PDF) para adjuntarlo a un hallazgo.
- Paginación si una ronda supera algunos cientos de sesiones.
