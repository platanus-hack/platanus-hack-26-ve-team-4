---
fecha: 2026-10-24
autor: "@franbastardo"
rama: feat/panel-monitor
pr: 44
estado: integrado
dominios: [frontend, arena, llm]
requisitos: []
---

# Panel de la empresa en `/monitor`

## Qué cambió

Nueva ruta `/monitor`, «Agent Zero Monitor», pensada para la empresa dueña del chatbot (Yummy). Sigue el diseño acordado en un artifact del equipo: franja de KPIs, feed de intentos | detalle con grafo, y tendencias abajo. Usa el mismo secreto de operador, sólo en memoria.

| Zona | Contenido | Fuente |
|---|---|---|
| KPIs | Intentos, violaciones, impedidos, señuelo, no logrados, inconclusos, tiempo de parcheo (mín–máx) y coste con número de llamadas | `GET /api/operator/monitor` |
| Feed | Hora, origen, versión, primer mensaje, resultado y familia; filtros por resultado | Ídem |
| Detalle | Familia, origen, política, tokens, llamadas, duración, parche y «activa N s después»; conversación; grafo de llamadas | `GET /api/operator/attempts/{id}` (`graph`) |
| Repetición | Si la violación tiene parche con repetición: pantalla dividida antes/después y tareas legítimas | `GET /api/arena/replay/{version}` |
| Tendencias | Violación por versión (ruta protegida con veredicto), versiones de política con reglas y tokens por intento | Monitor y `/api/operator/policies` |

Backend:

- `GET /api/operator/monitor` (`arena/monitor_router.py`, `arena/monitor_view.py`) devuelve una fila por intento. Cada fila trae:
  - resultado, ruta y familia: la de la campaña del Prober o, si no hay, la del analizador (`family_source`);
  - hallazgo y parche validado que lo cubre;
  - duración;
  - uso de modelo agregado desde el ledger LLM por `scope.attempt_id`. Incluye analizador y parcheador, que ya registran el `attempt_id`.
- `GET /api/operator/attempts/{id}` gana `graph`: las llamadas del propio intento, con el efecto indebido según los veredictos o la denegación del gateway con su control.
- `ProductCore.llm` expone el gateway LLM, solo para lectura.

## Por qué

`/operator` es la consola técnica: campañas, evaluación y reset. A la empresa le interesa otra pregunta: qué intentaron contra su agente, qué se bloqueó, cuánto tardó el parche y cuánto costó. Los tokens y las llamadas por intento ya estaban en el ledger, pero ninguna API los exponía.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/src/agent_zero/arena/monitor_view.py` | Nuevo: `usage_view`, `usage_by_attempt`, `attempt_row`, `attempt_patch` y `attempt_graph` |
| `backend/src/agent_zero/arena/monitor_router.py` | Nuevo: `GET /api/operator/monitor` |
| `backend/src/agent_zero/arena/operator_router.py` | `graph` en la evidencia del intento |
| `backend/src/agent_zero/arena/core.py`, `main.py` | Propiedad `llm` y registro del router |
| `backend/tests/arena/test_monitor_router.py` | Nuevo: secreto obligatorio; violación con hallazgo, parche, repetición, uso y grafo con efecto; intento impedido con arista bloqueada |
| `frontend/src/features/monitor/` | Nuevo: página, KPIs, feed, detalle, repetición, tendencias, estilos y pruebas |
| `frontend/src/features/arena/replay/AttackGraph.tsx` | El texto accesible distingue un grafo sin efecto indebido |
| `frontend/src/features/operator/api.ts` | `Policy` declara `created_at` y `activated_at` |
| `frontend/src/app/App.tsx` | Ruta y enlace «Monitor» |
| `docs/dominio/arena.md`, `docs/dominio/frontend.md` | Rutas y panel |

## Cómo se verificó

- Backend:
  - `tests/arena/test_monitor_router.py`: 2 passed;
  - `ruff check`, `ruff format --check` y `mypy src tests` limpios (619 archivos).
- Frontend:
  - `src/features/monitor`: 3 pruebas en verde (KPIs, feed, detalle con grafo, filtro, selección y 401/403);
  - Biome, `tsc -b` y build en verde;
  - suite completa: 94 de 95. La que falla es `AttemptChat` «cierra envío al pausar». Es intermitente: aislada pasó 1 de 3 veces, este cambio no la toca y no se comprobó contra `main` [SUPUESTO: ya era intermitente].
- Prueba manual por HTTP contra un backend `demo` con datos nuevos (puerto 8001), con 4 intentos de la audiencia:
  - uno legítimo (`not_achieved`);
  - una violación con hallazgo y parche v1 activo con repetición;
  - uno impedido, cuyo `graph` termina en una arista `blocked` con `order_belongs_to_session_customer`;
  - uno contenido en el señuelo.

  Llamadas por intento entre 2 y 4; tokens 0 porque el proveedor `simulated` no reporta uso.

## Riesgos y efectos en otros frentes

- **Ledger:** `/monitor` lee el JSONL completo del ledger LLM en cada consulta, cada 4 s. Sirve para una ronda de demo; con evaluaciones largas en el mismo `data_dir` conviene indexarlo.
- **Tokens en `demo`:** el proveedor simulado no reporta uso. El panel muestra «sin medir» y «simulado» en lugar de ceros.
- **Repetición:** la pantalla dividida viene de la traza que originó el parche. Si varios intentos comparten hallazgo, todos muestran esa misma repetición.
- **Contrato:** `graph` es un campo nuevo en la evidencia del operador; los consumidores que ignoran campos extra no cambian.

## Pendiente

- La familia «uso fuera de propósito» que proponía el diseño (pedir código o traducciones al bot) no existe en el backend. No se muestra.
- El diseño tenía un lado «con v0 llegaba al efecto» para los intentos impedidos; no hay traza de eso, así que se muestra solo el grafo propio.
