# `live` y `/arena`: Arena en vivo

Estado: implementado. Es la vista que se proyecta durante la demo, en `/arena`, detrás del acceso de operador. Sigue la maqueta aprobada (escenario fijo de 1920 × 1080):

- Un carrusel de 8 chats con 3 visibles.
- La barra de navegación.
- Cinco KPI.
- El Público enmascarado mientras la ronda no se revela.

Solo agrega datos que ya existen (intentos, sesiones, eventos, políticas, hallazgos, casos de campaña y el ledger de llamadas LLM). La única acción que ejecuta es «Cerrar acceso», que pausa y reanuda la ronda con el endpoint existente.

## Código

| Archivo | Función |
| --- | --- |
| [live/router.py](../../backend/src/agent_zero/live/router.py) | `GET /api/operator/live?sessions=N` (1 a 12, por defecto 6), con secreto de operador. |
| [live/service.py](../../backend/src/agent_zero/live/service.py) | `board_groups` (sesiones del tablero, con el Prober agrupado por campaña), `PatchIndex` (qué parche cubrió cada violación), `build_board` (función pura) y `LiveBoardService` (lecturas en bloque). |
| [live/models.py](../../backend/src/agent_zero/live/models.py) | Contrato v2. Su espejo en el frontend es [board/types.ts](../../frontend/src/features/board/types.ts). |
| [sessions/reserved_alias.py](../../backend/src/agent_zero/sessions/reserved_alias.py) | Prefijo `Agente-` reservado para el enjambre (`SWARM_PREFIX`, `is_reserved_alias`). |
| [llm/reporting.py](../../backend/src/agent_zero/llm/reporting.py) | `measured_tokens(records)`: suma tokens con uso medido; `None` si no hay. |
| [attack_swarm.py](../../backend/scripts/attack_swarm.py) | Enjambre de agentes simulados. |
| [features/board/](../../frontend/src/features/board/) | `BoardPage`, `BoardHeader`, `Carousel`, `ChatTile`, `KpiColumn`, `slots.ts`, `status.ts`, `vocabulary.ts`, `useStageScale.ts`, `api.ts` y `types.ts`. El CSS va separado por área: `stage.css`, `carousel.css`, `chat.css` y `kpi.css`. |
| [JoinCode.tsx](../../frontend/src/features/arena/JoinCode.tsx) | `JoinQr`: el QR compacto de la cabecera, con la misma URL pública que la tarjeta `JoinCode`. |
| [OperatorGate.tsx](../../frontend/src/features/operator/OperatorGate.tsx) | Acceso de operador compartido con `/operator`. |

Reutiliza `attempt_view` para redactar referencias de la respuesta, más `PolicyService.all()`, `FindingService.all()`, `ledger.records()` desde `app.state.llm`, `usePolling` y `operatorRequest`.

## Quién es cada sesión

| `kind` | Criterio | Cómo se muestra |
| --- | --- | --- |
| `audience` | Sesión `sess-…` cuyo alias no empieza por `Agente-` ni `Interno-`. | «Público». |
| `swarm` | Sesión `sess-…` con alias `Agente-…`. | «Agente simulado», siempre. |
| `prober` | Sesiones `internal-…` con alias `Prober`. | «Prober · xxxx». Cada caso de campaña abre su propia sesión interna, y el tablero las agrupa en una sola por `campaign_id`. Se muestra con los últimos 4 caracteres de la campaña. |
| `test` | Alias que empieza con `Interno-` (reservado: solo se crea con el secreto de operador, desde «Chat de prueba» en Operación). | «Prueba interna». Se muestra sin enmascarar y no cuenta en las KPI, en `sessions_total` ni en la clasificación pública. |

Una «sesión del tablero» es una sesión con al menos un intento. Las sesiones `internal-…` con alias «Repetición» (repeticiones del operador) se excluyen de las sesiones y de todas las KPI. `sessions_total` es el número de sesiones del tablero, con el Prober ya agrupado.

### Prefijo reservado del enjambre

`POST /api/sessions` rechaza con 409 cualquier alias que empiece por `Agente-`, salvo que la petición traiga `X-Operator-Secret`. La comparación ignora mayúsculas y espacios iniciales, y se aplica al alias recibido y también al alias ya redactado por Armor. Un secreto incorrecto responde 401. Por eso nadie del público puede hacerse pasar por el enjambre ni librarse del enmascarado. `Agentes` o `Agente 1` (sin guion) siguen permitidos.

### Prober agrupado

Una sesión agrupada del Prober se arma así:

- `session_id` es el `campaign_id`.
- La ruta es `honeypot` si alguna de sus sesiones internas lo es.
- `customer_id` es el del último intento.
- `attempt_total` cuenta todos sus casos.

Los `session_id` internos se conservan para atribuir los tokens del señuelo. Los del atacante se atribuyen por campaña.

## Enmascarado antes de revelar

Mientras `ArenaState.revealed` es falso, cada sesión `audience` lleva `concealed: true`. En el servidor:

- La sesión va con `route: null` y los contadores en `null`.
- Cada intento va con `outcome: null`, `route: null`, `reply: ""` y listas vacías de `denials` y `violated_objectives`.
- `patched_by` y `technique` van en `null`.

El texto de la respuesta no viaja en el JSON. Los mensajes del participante sí se muestran, porque son suyos. El enjambre y el Prober se muestran completos. Tras revelar, todo aparece con su ruta y su desenlace reales.

En pantalla, un chat enmascarado muestra:

- La burbuja «Respuesta oculta hasta revelar».
- El chip «Intento N · resultado oculto».
- La franja «Conversando · Oculto hasta revelar».
- Sin negaciones, sin separadores de parche y sin insignia de ruta.

Su indicador en la barra solo marca actividad (el anillo de evento) y nunca cambia de color.

## Contrato v2 (`GET /api/operator/live`)

Nivel superior:

- `revealed` y `accepting`, leído de `ArenaState`. `false` significa «Acceso cerrado».
- `llm_mode`, `policy_version` y `sessions_total`.
- `sessions` y `kpis`.
- `generated_at`, el reloj del servidor.

Cada sesión trae `concealed`, `contained_n`, `prevented_n` y `leaked_n`. Estos contadores se calculan sobre todos sus intentos terminados, no solo sobre los enviados. Se envían hasta los últimos 30 intentos por sesión.

Cada intento trae:

| Campo | Origen |
| --- | --- |
| `number` | Posición 1..N del intento en su sesión del tablero. |
| `policy_version`, `updated_at` | Del intento. |
| `denials[]` | Eventos `tool_denied` con visibilidad `operator`, en una sola consulta por `attempt_id IN (…)`. Solo `tool`, `reason` (valor de `GatewayReason`) y `validator`; nunca `arguments` ni `detail`. |
| `violated_objectives` | `assessment.verdicts` con `violated: true`. |
| `patched_by` | `{version, seconds_after}`: primera política que cubre un hallazgo del intento y cumple cuatro condiciones (ver abajo). |
| `technique` | `{family, mutator}` desde `CampaignCaseRecord.case_json` del caso del Prober. Es `null` para el enjambre y el Público: el servidor no conoce su plantilla. |

Condiciones de `patched_by`:

- La política está activada.
- No fue revertida (`rolled_back`).
- Su `version` es mayor que la del intento.
- Su `activated_at` es igual o posterior al `updated_at` del intento.

Solo aplica a intentos `confirmed_violation`. Un hallazgo reabierto acumula intentos posteriores al parche, y esos no quedan como «parcheados».

## Las cinco KPI

Cada KPI lleva su `n`, su fuente y, si cambia de alcance, `scope` y `label`. Todas cuentan solo intentos terminados (`evaluated` o `inconclusive`). Los que están en cola o en curso van en `attacks.in_flight` y no entran en ningún `n`.

| KPI | Contenido | Alcance |
| --- | --- | --- |
| `attacks` | Intentos terminados separados en `audience`, `swarm` y `prober`, más `in_flight`. | Toda la ronda. |
| `safe_space` | `safe_sessions`: sesiones en ruta `honeypot` con al menos un intento contenido, sobre `n`, las sesiones con alcance. Más `diverted_sessions` y `contained_attempts`. | `swarm_prober` hasta revelar; `all` después. |
| `leaked` | Intentos `confirmed_violation` sobre los intentos terminados con alcance. `by_objective` siempre trae `OBJ-ORDER`, `OBJ-MEMORY` y `OBJ-REFUND`. `objective_sum` puede superar `leaked`, porque un intento viola varios objetivos. | Igual que la anterior. |
| `attacker_tokens` | `attacker`: tokens del rol `prober` del ledger en las campañas del tablero. `decoy`: tokens del rol `decoy` en las sesiones internas con alcance. | Igual para `decoy`. |
| `patches` | `findings_total`: hallazgos con al menos un intento con alcance. `findings_covered`: hallazgos distintos de ese conjunto con una política activada y no revertida (siempre ≤ total). `activated`: versiones que los cubren. También `current_version` y la mediana desde la creación del hallazgo hasta la activación. | Igual que las anteriores: el Público sin revelar no mueve la cifra. |

`patches.median_seconds_to_patch` se mide desde la creación del hallazgo. En cambio, `patched_by.seconds_after` de cada intento se mide desde el cierre del intento. La pantalla no los mezcla: la KPI muestra la mediana y el chat muestra «Parche vN activado · X s después».

### Honestidad de los tokens

`measured_tokens` ignora las llamadas con origen `simulated` y las que no traen `usage`. Si no queda ninguna, la parte correspondiente va con `measured: false` y `tokens: null`. La KPI trae entonces `label`:

- «no medido en modo demo» cuando `llm_mode` es `demo`.
- «sin uso de tokens registrado» en otro modo.

La pantalla muestra «—», «No medido» y «(modo demo)», nunca un 0. Con `live`, `record` o `replay` con *cassette*, el ledger sí trae uso y se suma.

## Enjambre simulado

`scripts/attack_swarm.py` crea K sesiones (4 a 6) llamadas `Agente-1…K` y envía intentos con `POST /api/attempts` en paralelo. Espera el resultado de cada intento y luego un tiempo aleatorio.

Como el prefijo está reservado, el script necesita el secreto de operador. Lo lee de `AGENT_ZERO_OPERATOR_SECRET` (nunca de la línea de comandos) y no lo imprime. Lo envía solo en `POST /api/sessions`. Los intentos viajan con el token de participante, como los del público. Sin la variable, el script se detiene con un mensaje claro y no crea sesiones.

No escribe textos propios:

- Toma los casos de `prober/playbooks.py` (`campaign_case`).
- Aplica los mutadores `paraphrase_es`, `paraphrase_en` y `split_turns`.
- Cambia los pedidos de la plantilla por los de la sesión.

Solo viajan casos de superficie mensaje o memoria. El espaciado mínimo es de 5,2 s por sesión, muy por debajo del cupo de 240 intentos por minuto.

```bash
cd backend
AGENT_ZERO_OPERATOR_SECRET=... uv run python scripts/attack_swarm.py --base-url http://localhost:8000 --agents 5 --attempts 6
```

## Frontend

- **Ruta y acceso.** `/arena` monta `BoardPage` dentro de `OperatorGate`. El secreto vive solo en memoria. La barra de navegación se oculta solo mientras la Arena está abierta con el secreto (para proyectar); en el acceso y después de «Salir» vuelve a aparecer para ir a Participar, Monitor u Operación. La ruta `/tablero` y la arena pública anterior ya no existen. El backend público (`/api/arena/state`, `/events`, `/coevolution`) no cambió.
- **Escenario.** `useStageScale` escala el escenario de 1920 × 1080 por `min(w/1920, h/1080)`.
- **Consulta.** Se repite cada 1,5 s y pide 12 sesiones. `assignSlots` mantiene cada sesión en su lugar entre los 8 chats.
- **Cabecera.** Lleva:
  - La marca.
  - La píldora de estado: «En vivo», «Acceso cerrado» o «Ronda revelada».
  - «Mostrando 3 de 8 chats · N sesiones».
  - El modelo y el recuadro de revelación.
  - El QR (`JoinQr`).
  - «Cerrar acceso» o «Reabrir acceso», y «Salir».
- **Cerrar acceso.** Llama a `POST /api/operator/arena/pause|resume`. El botón queda bloqueado hasta que el tablero refleja el cambio, para evitar el doble clic, y un 409 del servidor se muestra en el margen inferior. Tras revelar, el servidor no permite reabrir: el botón desaparece y la píldora dice «Ronda revelada», no «Acceso cerrado».
- **Carrusel.** Navega con las flechas, los 8 indicadores (alias corto y punto de color), el marco deslizante, las teclas ← y → (salvo en un campo editable), el arrastre horizontal y el desplazamiento horizontal explícito: `deltaX` del trackpad o Shift+rueda, un chat por gesto. La rueda vertical sobre un chat no mueve el carrusel: es de la conversación. Sobre la barra de navegación la rueda vertical sí pasa un chat por gesto. Un arrastre con mouse que empieza vertical no mueve el carrusel. Los chats fuera de vista llevan `inert`. Se pueden fijar hasta 2: van a la izquierda y, al fijar un tercero, se suelta el más antiguo y se anuncia cuál.
- **Chat.** Tiene la cabecera con alias, quién ataca, la ruta y el botón «Fijar». Debajo:
  - La franja de estado: «Conversando», «Señal de riesgo», «Atacando» (solo enjambre y Prober), «En espacio seguro», «Se filtró», «Bloqueado» o «Acceso cerrado». «Bloqueado» solo aparece con un `prevented` o un parche vigente.
  - Buena fe: a una persona (Público) se la presume de buena fe. «Señal de riesgo» aparece solo con una herramienta negada por un validador, sin contar `rate_limited` ni `order_exists`; sin esa señal, la franja dice «Conversando · Sin señales de riesgo». Las burbujas del Público dicen «Participante» y las del enjambre y el Prober «Atacante». El KPI se llama «Intentos».
  - La conversación con todos los intentos recibidos (el servidor manda los últimos 30). Se desplaza en vertical con la rueda, el arrastre táctil o, con foco, ↑ ↓ Inicio Fin AvPág RePág, hasta el primer mensaje, sin que el desplazamiento se escape al carrusel ni a la página. Sigue al último mensaje mientras el usuario está abajo (margen de 24 px). Si subió a leer no se le mueve: aparece la píldora «↓ N nuevos», que vuelve al final al hacer clic y desaparece también al volver abajo a mano. El degradado superior solo aparece cuando hay contenido arriba. La lógica vive en `useConversationScroll`.
  - Las burbujas, con la técnica cuando se conoce.
  - El chip «Herramienta negada · …» con el mapa `DENIAL`. Si no conoce el motivo o el validador, cae a un texto legible.
  - Los chips por intento con el mapa `OUTCOME`.
  - Los separadores «Desviado a espacio seguro» y «Parche vN activado · X s después».
  - El pie «Intento N · hace X s», calculado contra `generated_at` y sin un total inventado, con una barra de 10 segmentos.
- **Eventos y movimiento.** Un cambio de estado marca el chat y su indicador 4 s. `prefers-reduced-motion` quita las animaciones.

## Pruebas

| Archivo | Cubre |
| --- | --- |
| [tests/live/test_board.py](../../backend/tests/live/test_board.py) | Clasificación y orden, numeración y límite de 30 intentos con contadores completos, enmascarado (el texto del Público no aparece en el JSON serializado), negaciones y técnica, Prober agrupado por campaña con tokens por campaña y por sesión interna, KPI sobre intentos terminados con `in_flight`, sesiones sin intentos fuera, `accepting`, tokens no medidos en demo, mediana de parcheo, política revertida y hallazgos del Público ignorados, `patched_by` con hallazgo reabierto. |
| [tests/live/test_router.py](../../backend/tests/live/test_router.py) | 401 sin secreto, validación de `sessions`, ronda vacía, recorrido real con enjambre (con cabecera de operador) y público hasta revelar, pausa y reanudación que se reflejan en `accepting`, secreto incorrecto con 401. |
| [tests/sessions/test_reserved_alias.py](../../backend/tests/sessions/test_reserved_alias.py) | `Agente-1`, `agente-1`, `AGENTE-9` y ` Agente-2` rechazados sin cabecera; aceptado con cabecera; 401 con secreto incorrecto; alias parecidos permitidos. |
| [tests/live/test_attack_swarm.py](../../backend/tests/live/test_attack_swarm.py) | Plantillas, pedidos de la sesión, semilla y límite de agentes. El secreto sale del entorno y solo viaja al crear la sesión. |
| [ChatTile.test.tsx](../../frontend/src/features/board/ChatTile.test.tsx) | Mapas `OUTCOME` y `DENIAL` con alternativas, técnica solo cuando se conoce, separadores de desvío y de parche, enmascarado sin texto en el DOM, «escribiendo», «Acceso cerrado» e `inert`. Conversación desplazable: todos los intentos, contador de mensajes, foco, degradado solo con contenido arriba y píldora «↓ N nuevos» que vuelve al final. |
| [useConversationScroll.test.tsx](../../frontend/src/features/board/useConversationScroll.test.tsx) | Arranque al final, seguir al último mensaje, margen de 24 px, contador de nuevos al leer arriba, vuelta al final a mano o con `jumpToEnd`, scroll suave salvo movimiento reducido y teclas. |
| [Carousel.test.tsx](../../frontend/src/features/board/Carousel.test.tsx) | 8 indicadores y 3 visibles, teclas, flechas, rueda sobre la barra, rueda vertical sobre un chat sin mover el carrusel, Shift+rueda, trackpad horizontal nativo, arrastre y arrastre vertical cancelado, indicadores, fijados a la izquierda y anillo de evento sin cambio de color. |
| [KpiColumn.test.tsx](../../frontend/src/features/board/KpiColumn.test.tsx) | Cinco tiles con las bases del servidor, «sin Público», «no medido en modo demo» sin ceros y sin porcentajes ni medianas inventadas. |
| [slots.test.ts](../../frontend/src/features/board/slots.test.ts) | Lugares estables, fijar con un máximo de 2, ventana, marcos, estado del chat, pulso enmascarado, «hace N s» y escala del escenario. |
| [BoardPage.test.tsx](../../frontend/src/features/board/BoardPage.test.tsx) | Acceso con cabecera, 8 chats con 3 a la vista y 5 KPI, Público sin texto, «Cerrar acceso» y «Reabrir acceso» con bloqueo del doble clic, 409 visible, «Ronda revelada» sin botón, fijado con aviso, «Salir» y 401. |
| [App.test.tsx](../../frontend/src/app/App.test.tsx) | `/arena` detrás de `OperatorGate` y sin barra; el menú ya no ofrece `/tablero`. |

jsdom no calcula el diseño, así que las medidas (448 × 856, sin desbordes) se comprobaron aparte: una captura a 1920 × 1080 con un navegador sin ventana, con datos simulados.

## Qué falta

- La prueba de punta a punta con el stack en modo `demo`, el enjambre y una campaña del Prober.
- Los tokens seguirán «no medidos» en modo `demo`; para ver cifras hay que ensayar con `live`, `record` o `replay`.
- Con mucho tráfico del público, el agregado debería calcularse en SQL en lugar de leer todos los intentos en cada consulta.
