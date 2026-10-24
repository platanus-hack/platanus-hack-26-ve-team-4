# `live` y `/tablero`: visión de ataque en vivo

Estado: implementado. Es una vista de solo lectura para proyectar: a la izquierda, hasta seis chats de atacantes mensaje a mensaje; a la derecha, cinco analíticas. No decide nada ni cambia rutas, veredictos o clasificación: agrega datos que ya existen (intentos, sesiones, políticas, hallazgos y el ledger de llamadas LLM).

## Código

| Archivo | Función |
| --- | --- |
| [live/router.py](../../backend/src/agent_zero/live/router.py) | `GET /api/operator/live?sessions=N` (1 a 12, por defecto 6), con secreto de operador. |
| [live/service.py](../../backend/src/agent_zero/live/service.py) | `build_board` (función pura sobre los datos ya leídos) y `LiveBoardService` (lee `core` y el ledger). |
| [live/models.py](../../backend/src/agent_zero/live/models.py) | Respuesta tipada: sesiones, intentos y las cinco KPI. |
| [llm/reporting.py](../../backend/src/agent_zero/llm/reporting.py) | `measured_tokens(records)`: suma tokens con uso medido; `None` si no hay. |
| [attack_swarm.py](../../backend/scripts/attack_swarm.py) | Enjambre de agentes simulados. |
| [features/board/](../../frontend/src/features/board/) | `BoardPage`, `ChatTile`, `KpiColumn`, `slots.ts`, `api.ts`, `types.ts` y `board.css`. |
| [OperatorGate.tsx](../../frontend/src/features/operator/OperatorGate.tsx) | Acceso de operador compartido con `OperatorPage`. |

Reutiliza `AttemptQueryService` y `attempt_view` (redacción de referencias y la regla pública de resultado aparente), `PolicyService.all()` (`policy_view`), `FindingService.all()`, `ledger.records()` desde `app.state.llm`, `usePolling`, `operatorRequest`, el mapa `OUTCOMES` de `AttemptList` y `formatDuration`.

## Quién es cada sesión

| `kind` | Criterio | Cómo se muestra |
| --- | --- | --- |
| `audience` | Sesión `sess-…` cuyo alias no empieza por `Agente-`. | «Público». |
| `swarm` | Sesión `sess-…` con alias `Agente-…`. | «Agente simulado», siempre. |
| `prober` | Sesión `internal-…` con alias `Prober`. | «Prober». Cada caso de una campaña abre su propia sesión; el tablero añade el final del identificador al nombre. |

Las sesiones `internal-…` con alias «Repetición» (repeticiones del operador) se excluyen de las sesiones y de todas las KPI.

Límite conocido: la clasificación del enjambre depende del alias. Una persona del público que elija `Agente-7` se verá como agente simulado y sin enmascarar. El tablero es de operación y no es una frontera de seguridad; si hiciera falta, la alternativa es marcar las sesiones del enjambre en el servidor.

## Enmascarado antes de revelar

Mientras `ArenaState.revealed` es falso, para las sesiones `audience`: `route` va como `null` (en la sesión y en cada intento) y `confirmed_violation`/`contained_honeypot` salen como `apparent_success`. Es la misma regla de `attempt_view` para el participante. El enjambre y el Prober se muestran completos. Tras revelar, todo se muestra con su ruta y desenlace reales. El frontend no pinta ninguna insignia de ruta cuando `route` es `null`.

## Las cinco KPI

Cada KPI lleva su `n` y su fuente.

| KPI | Contenido | Alcance |
| --- | --- | --- |
| `attacks` | Intentos de la ronda separados en `audience`, `swarm` y `prober`. | Toda la ronda. |
| `safe_space` | Sesiones con ruta `honeypot` sobre las sesiones con alcance, más los intentos `contained_honeypot`. | `swarm_prober` hasta revelar; `all` después. |
| `leaked` | Intentos `confirmed_violation` sobre los intentos con alcance, con desglose por objetivo violado (del veredicto de los oráculos). | Igual que la anterior. |
| `attacker_tokens` | `attacker`: tokens del rol `prober` del ledger en las campañas de la ronda. `decoy`: tokens del rol `decoy` en las sesiones con alcance. | Igual que la anterior para `decoy`. |
| `patches` | Versiones activadas sobre la base, versión vigente y mediana del tiempo desde `created_at` del hallazgo hasta `activated_at` de la política que lo cubre, con su `n`. | Toda la ronda. |

Las KPI 2 y 3 cuentan solo enjambre y Prober mientras no se revele, y la respuesta lo dice en `scope` y `label` («Solo enjambre y Prober hasta revelar»); el frontend lo muestra.

### Honestidad de los tokens

`measured_tokens` ignora las llamadas con origen `simulated` y las que no traen `usage`. Si no queda ninguna, la parte correspondiente va con `measured: false` y `tokens: null`, y la KPI trae `label`: «no medido en modo demo» cuando `llm_mode` es `demo`, o «sin uso de tokens registrado» en otro modo. El tablero muestra «No medido», nunca 0. Con `live`, `record` o `replay` con *cassette* el ledger sí trae uso y se suma.

Las llamadas del ledger se limitan a la ronda: las del Prober por las campañas de los intentos actuales, y las del señuelo por las sesiones con alcance. El ledger es un archivo persistente que sobrevive al reset de ronda.

## Respuesta (recortada)

```json
{
  "revealed": false, "llm_mode": "demo", "policy_version": 2,
  "sessions": [{
    "session_id": "sess-dd922ac8993d", "alias": "Agente-2", "kind": "swarm",
    "route": "honeypot", "last_activity": "2026-10-24T21:41:14+00:00", "attempt_total": 3,
    "attempts": [{"id": "attempt-6cdc5ad7ebe6", "status": "evaluated",
      "outcome": "confirmed_violation", "route": "protected", "messages": ["…"], "reply": "…"}]
  }],
  "kpis": {
    "attacks": {"n": 19, "audience": 0, "swarm": 15, "prober": 4},
    "safe_space": {"n": 5, "diverted_sessions": 5, "contained_attempts": 10, "scope": "swarm_prober"},
    "leaked": {"n": 15, "leaked": 5, "by_objective": {"OBJ-ORDER": 5, "OBJ-MEMORY": 3}},
    "attacker_tokens": {"measured": false, "label": "no medido en modo demo"},
    "patches": {"n": 2, "activated": 2, "current_version": 2, "median_seconds_to_patch": 10.111}
  }
}
```

Cada intento devuelve hasta los últimos 30 de su sesión (`attempt_total` trae el total). La consulta lee todos los intentos de la ronda en cada petición; es suficiente para una demo con cientos de intentos, no para miles.

## Enjambre simulado

`scripts/attack_swarm.py` crea K sesiones (4 a 6) llamadas `Agente-1…K` con `POST /api/sessions` y envía intentos con `POST /api/attempts` en paralelo, esperando el resultado de cada intento y luego un tiempo aleatorio. No usa el secreto de operador ni escribe textos propios: toma los casos de `prober/playbooks.py` (`campaign_case`), aplica los mutadores `paraphrase_es`, `paraphrase_en` y `split_turns` de `prober/mutators.py`, y cambia los pedidos de la plantilla por los de la sesión. Solo viajan casos de superficie mensaje o memoria; los de documento y resultado de herramienta necesitan fixtures del servidor y no se envían. El espaciado mínimo es de 5,2 s por sesión, bajo el cupo de 12 intentos por minuto.

```bash
cd backend
uv run python scripts/attack_swarm.py --base-url http://localhost:8000 --agents 5 --attempts 6
```

Opciones: `--agents` (4 a 6), `--attempts` por agente (1 a 30), `--min-wait`/`--max-wait` en segundos y `--seed`. El Prober se lanza aparte desde Operación (generación «Adaptativa») o con `POST /api/operator/campaigns`. El objetivo de cambio de dirección (D-04) no existe todavía en `main`; cuando entre en las plantillas el script lo tomará de `campaign_case` sin cambios.

## Frontend

- Ruta `/tablero`, protegida por `OperatorGate` (el mismo formulario que `/operator`; el secreto vive solo en memoria). La barra de navegación se oculta en esa ruta para proyectar a pantalla completa.
- Consulta cada 1,5 s con `usePolling` y pide 12 sesiones para poder reemplazar casillas. Seis casillas (2×3) cerca del 75 % del ancho y una columna fija de cinco KPI.
- `ChatTile`: alias, insignia de quién ataca (Público, Agente simulado, Prober), insignia de ruta (Protegido o Espacio seguro, solo si la ruta es visible), estado en texto además del color del borde (rojo si se dejó pasar, azul en el espacio seguro, verde si se bloqueó, neutro en curso), transcripción con «Asistente escribiendo…» mientras el intento está `queued` o `running`, chip con el desenlace por intento y desplazamiento automático al último mensaje.
- La prioridad del color es: ruta `honeypot` (azul), alguna violación confirmada (rojo), último desenlace detenido (verde). Una sesión que se dejó pasar y luego se desvió queda azul; su chip sigue en rojo.
- `slots.ts` mantiene cada sesión en su casilla. Una sesión nueva ocupa un hueco o reemplaza la casilla sin fijar con la actividad más antigua. Un clic en la casilla (o en «Fijar») la fija aunque salga de las más recientes.
- `prefers-reduced-motion` quita el parpadeo de «escribiendo…», la transición del borde y el desplazamiento suave.

## Pruebas

| Archivo | Cubre |
| --- | --- |
| [tests/live/test_board.py](../../backend/tests/live/test_board.py) | Clasificación, orden por actividad, exclusión de repeticiones, enmascarado antes y después de revelar, alcance de las KPI 2 y 3, tokens con `measured: false` y con un ledger falso, mediana de parcheo con marcas fijas. |
| [tests/live/test_router.py](../../backend/tests/live/test_router.py) | 401 sin secreto, validación de `sessions`, ronda vacía y recorrido real con enjambre y público hasta revelar. |
| [tests/live/test_attack_swarm.py](../../backend/tests/live/test_attack_swarm.py) | Solo mensajes viajan por la API pública, los pedidos son los de la sesión, reproducibilidad por semilla y límite de agentes. |
| [BoardPage.test.tsx](../../frontend/src/features/board/BoardPage.test.tsx) | Acceso con cabecera, seis chats y cinco KPI, colores por desenlace, «escribiendo…», enmascarado, fijar, «No medido» y asignación de casillas. |

## Qué falta

- Revisión visual en un navegador real y a distancia de proyección: las pruebas son DOM.
- Los tokens seguirán «no medidos» en modo `demo`; para mostrar cifras hay que ensayar con `live`, `record` o `replay`.
- Con mucho tráfico del público, el agregado debería calcularse en SQL en lugar de leer todos los intentos.
