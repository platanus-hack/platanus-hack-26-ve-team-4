# Frontend: participante, arena y operación

Estado: implementación revisada sobre la base funcional `1d0e21d`. React y TypeScript consumen la API del mismo origen. Las autorizaciones, resultados y puntuaciones se resuelven en el servidor; los estados visuales no sustituyen esos controles.

## Entradas y separación de responsabilidades

| Entrada | Función |
| --- | --- |
| [App.tsx](../../frontend/src/app/App.tsx) | Rutas `/` de participante, `/arena` (Arena en vivo, con secreto de operador), `/monitor`, `/auditoria`, `/consola` y `/operator`. |
| [ParticipantPage.tsx](../../frontend/src/features/participant/ParticipantPage.tsx) | Consentimiento, alta y recuperación mediante `/api/sessions/me`. |
| [AttemptChat.tsx](../../frontend/src/features/participant/AttemptChat.tsx) | Chat de soporte Yummy: burbujas, «escribiendo…», sugerencias y «Nueva conversación». Los mensajes seguidos salen juntos en un lote invisible a los 10 s del último; cada lote es un intento que continúa la conversación en curso (`continues`). |
| [richText.tsx](../../frontend/src/features/participant/richText.tsx) | Markdown mínimo de las respuestas de Yummy: `**negrita**` y viñetas `- ` o `* ` como «•», armado con elementos de React y sin HTML crudo. |
| [batch.ts](../../frontend/src/features/participant/batch.ts) | Tiempos del lote (`BATCH_IDLE_MS`, `TYPING_DELAY_MS`), tope (`QUEUE_MAX = 10`), vencimiento y armado del cuerpo (`packBatch`). |
| [useBatch.ts](../../frontend/src/features/participant/useBatch.ts), [BatchPreview.tsx](../../frontend/src/features/participant/BatchPreview.tsx) | Lote sin enviar: alarmas de 4 s y 10 s, persistencia, burbujas que se ven como enviadas y «escribiendo…». |
| [useConversation.ts](../../frontend/src/features/participant/useConversation.ts) | Envío durable, reconciliación del historial, conversaciones (`threadsOf`), reintento y espera de 429. |
| [LabPanel.tsx](../../frontend/src/features/participant/LabPanel.tsx) | Panel discreto del laboratorio: modo, identidad ficticia, pedidos, objetivos, límites y resultado provisional de cada mensaje. |
| [storage.ts](../../frontend/src/features/participant/storage.ts) | Sesión, historial pendiente y lote sin enviar en `localStorage`, con validación al leer; descarta la pulsera vencida y migra la que haya quedado en `sessionStorage`. |
| [OperatorPage.tsx](../../frontend/src/features/operator/OperatorPage.tsx) | Controles, campañas, políticas, hallazgos, evaluación y reset archivado. |
| [OperatorGate.tsx](../../frontend/src/features/operator/OperatorGate.tsx) | Acceso de operador con el secreto solo en memoria; lo usan `/operator`, `/arena` y `/auditoria`. `intro` agrega un encabezado mientras pide el secreto. |
| [BoardPage.tsx](../../frontend/src/features/board/BoardPage.tsx) | Ruta `/arena`: Arena en vivo de 1920 × 1080 con carrusel de 8 chats, cinco KPI, QR y «Cerrar acceso». Ver [Arena en vivo](./tablero.md). |
| [MonitorPage.tsx](../../frontend/src/features/monitor/MonitorPage.tsx) | Panel de la empresa en `/monitor`: KPIs de la ronda, feed de intentos con filtros, detalle con conversación y grafo, y tendencias (violación por versión, versiones de política, tokens por intento). |
| [AuditPage.tsx](../../frontend/src/features/audit/AuditPage.tsx) | Auditoría de chats en `/auditoria`: selector de ronda (en curso o archivada), lista de sesiones con búsqueda y filtros, e historial completo del chat elegido con su traza. La ronda y el chat viven en la URL (`?ronda=&chat=`). |
| [http.ts](../../frontend/src/shared/api/http.ts) | Errores tipados, timeout, cancelación y lectura de `Retry-After`. |
| [usePolling.ts](../../frontend/src/shared/api/usePolling.ts) | Consultas seriales y descarte de respuestas de un propietario anterior. |

Los contratos se declaran junto a cada feature, en [participant/types.ts](../../frontend/src/features/participant/types.ts), [arena/types.ts](../../frontend/src/features/arena/types.ts), [board/types.ts](../../frontend/src/features/board/types.ts) y [operator/api.ts](../../frontend/src/features/operator/api.ts). Cambiar un payload exige revisar esos tipos y las pruebas del consumidor correspondiente.

## Flujo del participante y fallos de red

Al recargar, cerrar la pestaña o abrir otra, se recupera el token del navegador (`localStorage`) y se valida contra `/api/sessions/me`; no se crea otra identidad ni se gasta otro cupo de la ronda. Todas las pestañas del mismo navegador son el mismo participante. Otro navegador o una ventana privada sí crean otra sesión: el servidor no puede distinguirlos. Un 401/403 invalida la sesión local. Un fallo de transporte conserva el token y permite volver a consultar.

Antes del POST se guarda una entrada con mensajes exactos y una clave aleatoria generada mediante `crypto.getRandomValues`, que funciona en HTTP local. La clave se conserva si se pierde la respuesta, incluso tras recargar. El historial consultado al servidor se reconcilia por ID o `idempotency_key`; una aceptación ya existente evita enviar de nuevo.

El chat envía un lote por intento con `continues` igual al último intento terminado de la conversación en curso. «Nueva conversación», o llegar a 6 intentos, envía el siguiente sin `continues`. Si el servidor rechaza la continuación con 404 o 409, el texto vuelve al campo y el mensaje siguiente abre una conversación nueva. Los resultados no aparecen en el chat, sino en el panel del laboratorio; antes de revelar, una violación y un éxito en el señuelo se ven igual.

### Lote invisible

«Enviar» (o Enter) muestra el mensaje en el chat como cualquier mensaje enviado, sin marca de pendiente, contador ni «Enviar ahora». Por dentro, los mensajes seguidos se juntan en un lote:

| Momento | Qué pasa | Constante en `batch.ts` |
| --- | --- | --- |
| 4 s sin un mensaje nuevo | Aparece «escribiendo…» y el encabezado dice «Escribiendo…». | `TYPING_DELAY_MS = 4_000` |
| 10 s sin un mensaje nuevo | El lote sale en un solo POST a `/api/attempts`. Cada mensaje nuevo reinicia la espera. | `BATCH_IDLE_MS = 10_000` |
| 10 mensajes sin respuesta | El lote sale sin esperar; si Yummy todavía responde, «Enviar» se desactiva, el texto queda en el campo y el chat pide esperar unos segundos. | `QUEUE_MAX = 10` |

Si al vencer el lote Yummy todavía responde al anterior, el lote sale apenas termina, porque el servidor admite una sola ejecución pendiente por sesión. `messages` lleva los textos unidos por saltos de línea; si no caben en `limits.message_max_length` (4000 por defecto), se agrupan en varios textos sin pasar ese largo. En el chat siguen viéndose como burbujas separadas: la entrada guarda `parts` además de `messages`, y la reconciliación las conserva. Si el navegador demora una alarma (pestaña en segundo plano), al volver se pone al día con la hora real. Con la ronda cerrada, el lote espera a que se reabran las entradas. Un envío sin confirmar (fallo de red o 429) también retiene el lote hasta reintentarlo.

El lote se guarda en `localStorage` (`agent-zero:batch:<sesión>`) con la hora del último mensaje: sobrevive a una recarga y se borra al salir el POST o al invalidar la pulsera. La entrada del intento se guarda antes del POST y el lote se borra en el mismo paso síncrono, así que una recarga no puede enviarlo dos veces.

### Concurrencia y errores

La interfaz no lanza un intento nuevo mientras existe una entrada pendiente o en ejecución, y dos envíos del formulario en el mismo evento agregan el texto una sola vez. Un 422 permite corregir el formulario; un 429 conserva la clave y respeta `Retry-After`. Las mutaciones no se reintentan silenciosamente desde el cliente HTTP.

Los límites vienen de la sesión, con compatibilidad de campos anterior. La UI muestra pausa de admisión y resultados provisionales. Tras revelar, vuelve a leer el resultado final propio; una lectura antigua no puede convertir una respuesta terminal en un intento en cola.

## Arena y operación

`usePolling` usa por defecto 2 s entre consultas completadas; el historial del chat usa 1,5 s. No solapa una lectura lenta con la siguiente y aborta/desestima respuestas al cambiar credenciales, ronda o componente. Ante errores conserva los últimos datos y muestra que pueden estar desactualizados.

La Arena en vivo consulta `GET /api/operator/live` cada 1,5 s; ya no hay una vista pública que use el SSE de `/api/arena/events` ni la co-evolución (el backend los sigue publicando). `useArenaState` sigue leyendo `/api/arena/state` para participante, monitor y operación.

La repetición del ataque vive en [replay/](../../frontend/src/features/arena/replay/). `useReplay` espera un `patch_validated` con `passed=true`, consulta `GET /api/arena/replay/{version}` y `ReplayStage` dibuja dos columnas (política anterior con el efecto en rojo, política nueva con la arista cortada y «bloqueado por política vN») y la fila de tareas legítimas. `AttackGraph` es SVG puro con texto además de color; con `prefers-reduced-motion` salta al estado final. Si la ruta responde 404 no se muestra nada. Muestra el rótulo «repetición de las llamadas a herramientas registradas»: el «antes» sale de la traza original y no se vuelve a ejecutar.

El panel de [monitor/](../../frontend/src/features/monitor/) usa el mismo secreto de operador en memoria y consulta `GET /api/operator/monitor` y `/api/operator/policies` cada 4 s. El detalle pide `GET /api/operator/attempts/{id}` y dibuja `graph` con `AttackGraph`. Si el intento es una violación cuyo parche tiene repetición, muestra la pantalla dividida de `/api/arena/replay/{version}` con las tareas legítimas. Las violaciones por versión cuentan sólo la ruta protegida con veredicto. Sin llamadas LIVE, los tokens se muestran como «sin medir» y el coste como «simulado».

La [auditoría](../../frontend/src/features/audit/) consulta `GET /api/operator/audit/rounds`, `/audit/chats` y `/audit/chats/{sesión}`. En la ronda en curso refresca cada 5 s; una ronda archivada no cambia y se lee una vez. Cada mensaje muestra las burbujas del chat de Yummy (`participant/chat.css`) con resultado, ruta, política y duración, los objetivos vulnerados y una traza plegable con cada llamada a herramienta. Antes del primer mensaje atendido en el señuelo aparece el aviso del desvío con su motivo. El mensaje y cada paso de la traza son los componentes compartidos [audit/Exchange.tsx](../../frontend/src/features/audit/Exchange.tsx) y [audit/ToolStep.tsx](../../frontend/src/features/audit/ToolStep.tsx), que también usa la consola.

### Consola de pruebas (`/consola`)

Ruta protegida con `OperatorGate` (secreto de operador solo en memoria) y enlace «Consola» en la navegación de [App.tsx](../../frontend/src/app/App.tsx). Junta en una pantalla un chat de prueba y su auditoría en vivo, para probar mensajes y ver cómo los clasifica el agente.

| Archivo | Función |
| --- | --- |
| [ConsolePage.tsx](../../frontend/src/features/consola/ConsolePage.tsx) | Encabezado con «Nueva sesión», selector de sesiones anteriores, «Abrir en Auditoría» y «Salir». A la izquierda `AttemptChat`; a la derecha `LiveAudit`. |
| [consoleSession.ts](../../frontend/src/features/consola/consoleSession.ts) | Sesión actual y lista de sesiones previas, en su propio almacenamiento. |
| [LiveAudit.tsx](../../frontend/src/features/consola/LiveAudit.tsx) | Auditoría de la sesión que se refresca sola. |
| [consola.css](../../frontend/src/features/consola/consola.css) | Disposición de dos columnas; en pantallas angostas se apilan. |

- **Sesión.** Si no hay una guardada, al entrar se crea una sesión `Interno-consola-<sufijo>` con `POST /api/sessions` y el secreto de operador (`testAlias` la recorta a 40 caracteres). Se guarda en `localStorage` con la clave `agent-zero:consola:v1`, separada de la pulsera del participante (`agent-zero:participant:v1`): abrir la consola no reemplaza la sesión del participante. Si la sesión vence, la consola crea otra.
- **Nueva sesión.** Crea una sesión nueva y archiva la anterior en `agent-zero:consola:past:v1`: hasta 20, la más reciente primero, con id, alias y fecha. El historial local de la sesión anterior (`agent-zero:history:<id>`) no se borra.
- **Sesiones anteriores.** El selector abre `/auditoria?chat=<id>` en otra pestaña. Esa ruta busca el chat en la ronda en curso. Una sesión de una ronda archivada necesita además `ronda=<archive_id>` en la URL, y la consola todavía no lo añade.
- **Chat.** `AttemptChat` se reutiliza sin cambios, con la sesión de la consola. El envío, el lote y «Nueva conversación» funcionan como en el participante.
- **Auditoría en vivo.** `LiveAudit` consulta `GET /api/operator/audit/chats/{id}` cada 1,5 s con `usePolling` y `X-Operator-Secret`. Un chat sin mensajes responde 404 y se muestra una guía, no un error. Arriba aparecen la ruta, el riesgo (`risk_score`), las violaciones, la cantidad de mensajes, las señales de riesgo (`risk_signals`, validador y veces) y el desvío al señuelo. Debajo, una tarjeta `Exchange` por mensaje, con el más reciente primero, que muestra:
  - el desenlace y el estado del intento;
  - familia, ruta y los validadores que negaron llamadas («Negado por …»);
  - lo escrito y la respuesta de Yummy, con el objetivo vulnerado si lo hubo;
  - la traza abierta, con cada paso de herramienta. En los pasos denegados, el motivo de Armor con su etapa y su detalle, cuando el evento los trae.
- **Clasificación.** Las sesiones de la consola salen como «Prueba interna» en el tablero y en la auditoría. No cuentan en las KPI, en `sessions_total` ni en la clasificación (ver [Arena](./arena.md)).

### Chats automáticos (`/demo`)

Ruta protegida con `OperatorGate` y enlace «Chats automáticos» en la navegación. La Arena en vivo trae el mismo lanzador en su cabecera, en el botón «Chat interno» junto a «Modelo» ([InternalChatButton.tsx](../../frontend/src/features/demo/InternalChatButton.tsx)): el diálogo se abre encima del escenario y los chats aparecen en el carrusel como «Prueba interna». Lanza a la vez hasta 6 chats guionizados contra el entorno en el que corre y muestra cada conversación en vivo, con su ruta y su veredicto. Los casos salen de la escala de intención humana 0–5: los niveles 0 a 2 son clientes legítimos y los niveles 3 a 5, atacantes.

| Archivo | Función |
| --- | --- |
| [catalog.ts](../../frontend/src/features/demo/catalog.ts) | Tipos, nombres de nivel, los 6 recomendados (`N0-2`, `N1-1`, `N2-1`, `N3-2`, `N4-2`, `N5-1`) y el tope de 6 chats. |
| [casesLegit.ts](../../frontend/src/features/demo/casesLegit.ts) y [casesAttack.ts](../../frontend/src/features/demo/casesAttack.ts) | 16 casos con sus turnos. Quedan fuera N5-2 y N5-3: necesitan fixtures controlados que solo instala el Prober. |
| [fill.ts](../../frontend/src/features/demo/fill.ts) | Rellena `{own}`, `{own_delivered}`, `{f}`, `{g_delivered}` y demás con los pedidos de la sesión y los de un cliente semilla ajeno. Si la sesión es de Carla o de Bruno, cambia de cliente ajeno. |
| [runner.ts](../../frontend/src/features/demo/runner.ts) | Un chat: crea la sesión `Interno-Auto-<caso>-<persona>-<n>` con el secreto, manda cada turno con `continues` al anterior y espera el desenlace con `GET /api/attempts/{id}`. Reintenta los 429. |
| [useSwarm.ts](../../frontend/src/features/demo/useSwarm.ts) | Arranca todos los chats a la vez y los detiene con un `AbortController`. |
| [verdict.ts](../../frontend/src/features/demo/verdict.ts) | Veredicto por chat y resumen con los datos de `GET /api/operator/live`. Para un legítimo, el desvío al señuelo es un falso positivo; para un atacante, el desvío o el cierre sin filtración cuentan como contenido. Una `confirmed_violation` es filtración en ambos. |
| [DemoPage.tsx](../../frontend/src/features/demo/DemoPage.tsx), [LaunchDialog.tsx](../../frontend/src/features/demo/LaunchDialog.tsx), [DemoChat.tsx](../../frontend/src/features/demo/DemoChat.tsx), [DemoSummary.tsx](../../frontend/src/features/demo/DemoSummary.tsx) | Botón «Lanzar chats automáticos», diálogo (cuántos chats y qué caso lleva cada uno), cuadrícula de chats y franja de resultado con cronómetro contra la meta de 90 s. |

- **Datos en vivo.** La ruta, el desenlace y las negaciones del gateway vienen de `GET /api/operator/live?sessions=12`, que consulta cada 1,5 s. Las sesiones `Interno-` llegan sin enmascarar, y la respuesta de Yummy también llega por el intento del participante.
- **Clasificación.** Son pruebas internas: salen como «Prueba interna» en la Arena en vivo y no entran en la clasificación pública. A diferencia del resto de los `Interno-`, el prefijo `Interno-Auto-` sí mueve las KPI y `sessions_total` (`counts_in_analytics` en `sessions/reserved_alias.py`), para que la demo se vea en las analíticas. Cada chat ocupa una identidad sintética de la ronda.
- **Modo.** El encabezado muestra `llm_mode`. En `demo` responde el motor de reglas, así que el texto de los casos solo se lee natural en `live`.

[JoinCode.tsx](../../frontend/src/features/arena/JoinCode.tsx) genera SVG local con `qrcode`. Acepta HTTP/HTTPS sin usuario ni contraseña y normaliza el enlace a la raíz del origen. Usa `VITE_PUBLIC_PARTICIPANT_URL` de build o el origen actual; también se puede editar en la tarjeta. Ese cambio no publica un despliegue. `JoinQr` dibuja el mismo QR, compacto, en la cabecera de la Arena en vivo.

Operación mantiene el secreto sólo en memoria durante la visita. Todas sus peticiones usan `X-Operator-Secret`, y un rechazo de autorización borra el acceso. Un bloqueo local serializa acciones, incluso un doble clic anterior al render siguiente. Cada mutación tiene que solicitarse explícitamente otra vez si se pierde su respuesta.

La pantalla permite inspeccionar/descargar evidencia de intentos e informes de evaluación, lanzar/detener campañas y evaluaciones, repetir, revertir, pausar/revelar y resetear con motivo. Las explicaciones de analizador/parche se muestran como asesoría. El servidor conserva la decisión final, incluidas las condiciones de drenaje que el cliente sólo anticipa visualmente.

## Desarrollo y comprobación

Desde la raíz, seguir primero [desarrollo](../desarrollo.md). El backend debe estar en marcha y Vite redirige `/api` a `http://localhost:8000`:

```bash
make dev-frontend
```

Para otro backend: `VITE_API_PROXY=http://localhost:8001 make dev-frontend`. La configuración está en [vite.config.ts](../../frontend/vite.config.ts).

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Para revisar un flujo concreto:

```bash
cd frontend
pnpm exec vitest run src/features/participant
pnpm exec vitest run src/features/operator/OperatorPage.test.tsx
pnpm exec vitest run src/features/board src/shared/api
```

| Archivos de pruebas | Comportamiento cubierto |
| --- | --- |
| [ParticipantPage.test.tsx](../../frontend/src/features/participant/ParticipantPage.test.tsx), [storage.test.ts](../../frontend/src/features/participant/storage.test.ts) | Consentimiento, alta, recuperación, expiración/reset, JSON corrupto y almacenamiento no disponible. |
| [AttemptChat.test.tsx](../../frontend/src/features/participant/AttemptChat.test.tsx), [AttemptChat.compose.test.tsx](../../frontend/src/features/participant/AttemptChat.compose.test.tsx) | Respuesta perdida, recarga, reconciliación sin duplicar, cuatro turnos, doble envío, frecuencia, revelación sin filtrar ruta y redacción mientras Yummy responde. |
| [AttemptChat.batch.test.tsx](../../frontend/src/features/participant/AttemptChat.batch.test.tsx), [batch.test.ts](../../frontend/src/features/participant/batch.test.ts) | Lote invisible con reloj falso: «escribiendo…» a los 4 s, envío a los 10 s del último mensaje, espera a que Yummy termine, tope de 10 mensajes, agrupación por largo y recarga. |
| [OperatorPage.test.tsx](../../frontend/src/features/operator/OperatorPage.test.tsx) | Autorización, secreto no persistido, acciones seriales, evidencia, reset y evaluación explícita. |
| [board/](../../frontend/src/features/board/) (`BoardPage`, `ChatTile`, `Carousel`, `KpiColumn`, `slots`), [App.test.tsx](../../frontend/src/app/App.test.tsx) | Arena en vivo: acceso, carrusel, Público completo en vivo, Marcador provisional/final, mapas de desenlace y negación, KPI honestas, «Cerrar acceso» y la ruta `/arena`. |
| [AuditPage.test.tsx](../../frontend/src/features/audit/AuditPage.test.tsx) | Auditoría: acceso, filtros y búsqueda, historial con veredicto, traza y aviso de desvío, enlace directo a un chat y cambio a una ronda archivada. |
| [Exchange.test.tsx](../../frontend/src/features/audit/Exchange.test.tsx) | Mensaje de la auditoría con y sin el modo `live`: clasificación, negaciones de validador y motivo de Armor en los pasos denegados. |
| [consoleSession.test.ts](../../frontend/src/features/consola/consoleSession.test.ts), [ConsolePage.test.tsx](../../frontend/src/features/consola/ConsolePage.test.tsx), [LiveAudit.test.tsx](../../frontend/src/features/consola/LiveAudit.test.tsx) | Clave propia de la consola, lista de sesiones previas (máximo 20), «Nueva sesión» y la auditoría en vivo. |
| [http.test.ts](../../frontend/src/shared/api/http.test.ts), [usePolling.test.ts](../../frontend/src/shared/api/usePolling.test.ts) | Timeout/cancelación, `Retry-After`, datos previos, ausencia de solapamiento y respuestas antiguas. |

La ejecución previa aprobó 47 pruebas, lint, TypeScript y build. El proxy y el ejercicio completo se verificaron con imágenes Docker reales. Esas verificaciones son DOM/HTTP; no hubo revisión visual de navegador disponible. La [guía de evidencias](../pruebas/evidencias.md) conserva la diferencia.

## Qué completar después

La UI de reset muestra el `archive_id`; listar y descargar archivos de rondas previas sigue siendo una operación de API. Falta revisión visual y de accesibilidad en móvil/navegador, además de QR desde un teléfono contra un despliegue publicado. Al ampliar un flujo, mantener el estado de recuperación, la idempotencia y los tests de respuestas tardías antes de modificar la presentación.

## Arena en vivo sin enmascarado

`ChatTile` muestra las sesiones de audiencia completas desde el primer intento: mensaje, respuesta del bot, etiqueta de ruta (protegida o señuelo), negaciones con su motivo y chip de desenlace por intento. Ya no existen los textos «Oculto hasta revelar», «Respuesta oculta hasta revelar» ni el chip de resultado oculto. El componente `board/Scoreboard.tsx`, alimentado por `useArenaState` sobre `/api/arena/state`, muestra «Marcador provisional» (puntos aparentes, incluidos los del señuelo) antes de revelar y «Marcador final» con «N aparentes · S confirmados · C en el señuelo» después. `KpiColumn` ya no añade « sin Público». El Marcador muestra en vivo «Confirmadas» y «En el señuelo» (con el texto completo como descripción emergente). Las negaciones se etiquetan desde `control`, sin depender del id del validador. Las sesiones «Prueba interna» y las de enjambre no cambian.

- Tipos: `LiveSession` sin `concealed`, con `route: RouteName` y contadores numéricos; `LiveAttempt.route: RouteName`.
- Medidas comprobadas con captura a 1920x1080 (25-oct-2026): tiles de Analíticas de 146 px (número de 56 px, filas de 24 px) y Marcador de 115 px (letra de 18 a 20 px, top 2); ni las tiles ni el Marcador desbordan. [SUPUESTO] Alias muy largos en el Marcador se cortan con puntos suspensivos; no se probó con más de un participante con puntos.
- Mientras `/api/arena/state` no responde, el Marcador muestra «Marcador no disponible».
