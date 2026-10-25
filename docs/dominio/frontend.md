# Frontend: participante, arena y operación

Estado: implementación revisada sobre la base funcional `1d0e21d`. React y TypeScript consumen la API del mismo origen. Las autorizaciones, resultados y puntuaciones se resuelven en el servidor; los estados visuales no sustituyen esos controles.

## Entradas y separación de responsabilidades

| Entrada | Función |
| --- | --- |
| [App.tsx](../../frontend/src/app/App.tsx) | Rutas `/` de participante, `/arena` (Arena en vivo, con secreto de operador), `/monitor` y `/operator`. |
| [ParticipantPage.tsx](../../frontend/src/features/participant/ParticipantPage.tsx) | Consentimiento, alta y recuperación mediante `/api/sessions/me`. |
| [AttemptChat.tsx](../../frontend/src/features/participant/AttemptChat.tsx) | Chat de soporte Yummy: burbujas, «escribiendo…», sugerencias y «Nueva conversación». Los mensajes se juntan en un lote y cada lote es un intento que continúa la conversación en curso (`continues`). |
| [batch.ts](../../frontend/src/features/participant/batch.ts) | Constantes del lote (`BATCH_IDLE_MS`, `BATCH_MAX_WAIT_MS`, `BATCH_MAX_MESSAGES`), vencimiento y armado del cuerpo (`packBatch`). |
| [useBatch.ts](../../frontend/src/features/participant/useBatch.ts), [BatchPreview.tsx](../../frontend/src/features/participant/BatchPreview.tsx) | Lote pendiente: contador, envío al vencer o con «Enviar ahora», persistencia; burbujas pendientes y barra con la cuenta regresiva. |
| [useConversation.ts](../../frontend/src/features/participant/useConversation.ts) | Envío durable, reconciliación del historial, conversaciones (`threadsOf`), reintento y espera de 429. |
| [LabPanel.tsx](../../frontend/src/features/participant/LabPanel.tsx) | Panel discreto del laboratorio: modo, identidad ficticia, pedidos, objetivos, límites y resultado provisional de cada mensaje. |
| [storage.ts](../../frontend/src/features/participant/storage.ts) | Sesión, historial pendiente y lote sin enviar en `localStorage`, con validación al leer; descarta la pulsera vencida y migra la que haya quedado en `sessionStorage`. |
| [OperatorPage.tsx](../../frontend/src/features/operator/OperatorPage.tsx) | Controles, campañas, políticas, hallazgos, evaluación y reset archivado. |
| [OperatorGate.tsx](../../frontend/src/features/operator/OperatorGate.tsx) | Acceso de operador con el secreto solo en memoria; lo usan `/operator` y `/arena`. |
| [BoardPage.tsx](../../frontend/src/features/board/BoardPage.tsx) | Ruta `/arena`: Arena en vivo de 1920 × 1080 con carrusel de 8 chats, cinco KPI, QR y «Cerrar acceso». Ver [Arena en vivo](./tablero.md). |
| [MonitorPage.tsx](../../frontend/src/features/monitor/MonitorPage.tsx) | Panel de la empresa en `/monitor`: KPIs de la ronda, feed de intentos con filtros, detalle con conversación y grafo, y tendencias (violación por versión, versiones de política, tokens por intento). |
| [http.ts](../../frontend/src/shared/api/http.ts) | Errores tipados, timeout, cancelación y lectura de `Retry-After`. |
| [usePolling.ts](../../frontend/src/shared/api/usePolling.ts) | Consultas seriales y descarte de respuestas de un propietario anterior. |

Los contratos se declaran junto a cada feature, en [participant/types.ts](../../frontend/src/features/participant/types.ts), [arena/types.ts](../../frontend/src/features/arena/types.ts), [board/types.ts](../../frontend/src/features/board/types.ts) y [operator/api.ts](../../frontend/src/features/operator/api.ts). Cambiar un payload exige revisar esos tipos y las pruebas del consumidor correspondiente.

## Flujo del participante y fallos de red

Al recargar, cerrar la pestaña o abrir otra, se recupera el token del navegador (`localStorage`) y se valida contra `/api/sessions/me`; no se crea otra identidad ni se gasta otro cupo de la ronda. Todas las pestañas del mismo navegador son el mismo participante. Otro navegador o una ventana privada sí crean otra sesión: el servidor no puede distinguirlos. Un 401/403 invalida la sesión local. Un fallo de transporte conserva el token y permite volver a consultar.

Antes del POST se guarda una entrada con mensajes exactos y una clave aleatoria generada mediante `crypto.getRandomValues`, que funciona en HTTP local. La clave se conserva si se pierde la respuesta, incluso tras recargar. El historial consultado al servidor se reconcilia por ID o `idempotency_key`; una aceptación ya existente evita enviar de nuevo.

El chat envía un lote por intento con `continues` igual al último intento terminado de la conversación en curso. «Nueva conversación», o llegar a 6 intentos, envía el siguiente sin `continues`. Si el servidor rechaza la continuación con 404 o 409, el texto vuelve al campo y el mensaje siguiente abre una conversación nueva. Los resultados no aparecen en el chat, sino en el panel del laboratorio; antes de revelar, una violación y un éxito en el señuelo se ven igual.

### Mensajes en lote

«Enviar» (o Enter) no llama al servidor: el mensaje entra a un lote pendiente que se ve en el chat como burbuja propia atenuada, con la marca «Pendiente», y el campo queda libre para el siguiente. Una barra encima del campo dice cuántos mensajes hay y «Se envía en N s», con el botón «Enviar ahora». El lote vence con lo primero que ocurra:

| Condición | Constante en `batch.ts` |
| --- | --- |
| 10 s sin un mensaje nuevo; cada mensaje reinicia la espera | `BATCH_IDLE_MS = 10_000` |
| 20 s desde el primer mensaje del lote | `BATCH_MAX_WAIT_MS = 20_000` |
| 4 mensajes juntos (o `limits.max_messages`, si es menor) | `BATCH_MAX_MESSAGES = 4` |
| «Enviar ahora» | — |

El lote vencido sale en un solo POST a `/api/attempts`, con una clave idempotente nueva: `messages` lleva un único texto con los mensajes unidos por saltos de línea; si ese texto supera `limits.message_max_length` (4000 por defecto), `messages` lleva los mensajes por separado (hasta 4, cada uno ya limitado por el campo). En el chat siguen viéndose como burbujas separadas: la entrada guarda `parts` además de `messages`, y la reconciliación las conserva.

Mientras Yummy responde se puede seguir escribiendo; esos mensajes arman el lote siguiente y su contador corre. Si vence antes de que termine el intento anterior, la barra dice «Se envía cuando Yummy termine de responder» y el lote sale al terminar ese intento (el servidor admite una ejecución pendiente por sesión). Con 4 mensajes esperando, «Enviar» se desactiva hasta que el lote salga; el texto queda en el campo. Con la ronda cerrada, el lote espera a que se reabran las entradas. Un envío sin confirmar (fallo de red o 429) también retiene el lote siguiente hasta reintentarlo.

El lote se guarda en `localStorage` (`agent-zero:batch:<sesión>`) con la hora del primer y del último mensaje: sobrevive a una recarga, conserva el tiempo transcurrido y se borra al salir el POST o al invalidar la pulsera. La entrada del intento se guarda antes del POST y el lote se borra en el mismo paso síncrono, así que una recarga no puede enviarlo dos veces.

### Concurrencia y errores

La interfaz no lanza un intento nuevo mientras existe una entrada pendiente o en ejecución, y dos envíos del formulario en el mismo evento agregan el texto una sola vez. Un 422 permite corregir el formulario; un 429 conserva la clave y respeta `Retry-After`. Las mutaciones no se reintentan silenciosamente desde el cliente HTTP.

Los límites vienen de la sesión, con compatibilidad de campos anterior. La UI muestra pausa de admisión y resultados provisionales. Tras revelar, vuelve a leer el resultado final propio; una lectura antigua no puede convertir una respuesta terminal en un intento en cola.

## Arena y operación

`usePolling` usa por defecto 2 s entre consultas completadas; el historial del chat usa 1,5 s. No solapa una lectura lenta con la siguiente y aborta/desestima respuestas al cambiar credenciales, ronda o componente. Ante errores conserva los últimos datos y muestra que pueden estar desactualizados.

La Arena en vivo consulta `GET /api/operator/live` cada 1,5 s; ya no hay una vista pública que use el SSE de `/api/arena/events` ni la co-evolución (el backend los sigue publicando). `useArenaState` sigue leyendo `/api/arena/state` para participante, monitor y operación.

La repetición del ataque vive en [replay/](../../frontend/src/features/arena/replay/). `useReplay` espera un `patch_validated` con `passed=true`, consulta `GET /api/arena/replay/{version}` y `ReplayStage` dibuja dos columnas (política anterior con el efecto en rojo, política nueva con la arista cortada y «bloqueado por política vN») y la fila de tareas legítimas. `AttackGraph` es SVG puro con texto además de color; con `prefers-reduced-motion` salta al estado final. Si la ruta responde 404 no se muestra nada. Muestra el rótulo «repetición de las llamadas a herramientas registradas»: el «antes» sale de la traza original y no se vuelve a ejecutar.

El panel de [monitor/](../../frontend/src/features/monitor/) usa el mismo secreto de operador en memoria y consulta `GET /api/operator/monitor` y `/api/operator/policies` cada 4 s. El detalle pide `GET /api/operator/attempts/{id}` y dibuja `graph` con `AttackGraph`. Si el intento es una violación cuyo parche tiene repetición, muestra la pantalla dividida de `/api/arena/replay/{version}` con las tareas legítimas. Las violaciones por versión cuentan sólo la ruta protegida con veredicto. Sin llamadas LIVE, los tokens se muestran como «sin medir» y el coste como «simulado».

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
| [AttemptChat.batch.test.tsx](../../frontend/src/features/participant/AttemptChat.batch.test.tsx), [batch.test.ts](../../frontend/src/features/participant/batch.test.ts) | Lote con temporizadores falsos: espera de 10 s que se reinicia, tope de 20 s, cuarto mensaje, «Enviar ahora», unión y división por largo, lote siguiente durante un intento, lote lleno y recarga. |
| [OperatorPage.test.tsx](../../frontend/src/features/operator/OperatorPage.test.tsx) | Autorización, secreto no persistido, acciones seriales, evidencia, reset y evaluación explícita. |
| [board/](../../frontend/src/features/board/) (`BoardPage`, `ChatTile`, `Carousel`, `KpiColumn`, `slots`), [App.test.tsx](../../frontend/src/app/App.test.tsx) | Arena en vivo: acceso, carrusel, enmascarado, mapas de desenlace y negación, KPI honestas, «Cerrar acceso» y la ruta `/arena`. |
| [http.test.ts](../../frontend/src/shared/api/http.test.ts), [usePolling.test.ts](../../frontend/src/shared/api/usePolling.test.ts) | Timeout/cancelación, `Retry-After`, datos previos, ausencia de solapamiento y respuestas antiguas. |

La ejecución previa aprobó 47 pruebas, lint, TypeScript y build. El proxy y el ejercicio completo se verificaron con imágenes Docker reales. Esas verificaciones son DOM/HTTP; no hubo revisión visual de navegador disponible. La [guía de evidencias](../pruebas/evidencias.md) conserva la diferencia.

## Qué completar después

La UI de reset muestra el `archive_id`; listar y descargar archivos de rondas previas sigue siendo una operación de API. Falta revisión visual y de accesibilidad en móvil/navegador, además de QR desde un teléfono contra un despliegue publicado. Al ampliar un flujo, mantener el estado de recuperación, la idempotencia y los tests de respuestas tardías antes de modificar la presentación.
