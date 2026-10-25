---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: feat/chat-mensajes-en-lote
pr: pendiente
estado: en revisión
dominios: [frontend]
requisitos: []
---

# El chat del participante junta los mensajes en lote antes de enviarlos

## Qué cambió

Antes, cada mensaje del chat era un intento aparte y el envío se bloqueaba («Esperando respuesta…») mientras Yummi respondía. Ahora «Enviar» o Enter agrega el mensaje a un lote pendiente, que se ve en el chat como burbuja propia atenuada con la marca «Pendiente». El lote sale como un solo intento con lo primero que ocurra:

| Condición | Constante (`frontend/src/features/participant/batch.ts`) |
|---|---|
| 10 s sin un mensaje nuevo; cada mensaje reinicia la espera | `BATCH_IDLE_MS` |
| 20 s desde el primer mensaje del lote | `BATCH_MAX_WAIT_MS` |
| 4 mensajes juntos (o `limits.max_messages`, si es menor) | `BATCH_MAX_MESSAGES` |
| Botón «Enviar ahora», junto a la cuenta «Se envía en N s» | — |

| Caso | Comportamiento |
|---|---|
| Cuerpo del POST | Un único POST a `/api/attempts` con `messages: [texto]`, los mensajes unidos con saltos de línea. Si el texto unido supera `limits.message_max_length` (4000 por defecto), `messages` lleva los mensajes por separado (hasta 4). |
| Vista tras el envío | Las burbujas siguen separadas: la entrada guarda `parts` (lo escrito) además de `messages` (lo enviado) y `mergeHistory` las conserva. |
| Yummi está respondiendo | Se puede seguir escribiendo; los mensajes arman el lote siguiente y su contador corre. Si vence antes, la barra dice «Se envía cuando Yummi termine de responder» y el lote sale al terminar el intento anterior. El servidor sigue admitiendo una ejecución pendiente por sesión. |
| Lote lleno mientras espera | «Enviar» se desactiva; el texto queda en el campo hasta que el lote salga. |
| Ronda cerrada | El lote espera a que se reabran las entradas. |
| Envío sin confirmar (red o 429) | El lote siguiente espera a que se reintente; la clave idempotente y `Retry-After` no cambian. |
| Recarga | El lote vive en `localStorage` (`agent-zero:batch:<sesión>`) con la hora del primer y del último mensaje; tras recargar se ve igual y conserva el tiempo transcurrido. Se borra al salir el POST, en el mismo paso síncrono en que se guarda la entrada del intento, y al invalidar la pulsera. |

## Por qué

Fernando pidió que la persona pueda mandar varios mensajes seguidos, como en un chat de mensajería, sin quedar bloqueada mientras Yummi responde. Juntar la ráfaga en un intento también evita gastar un intento por cada línea suelta del límite de frecuencia.

## Archivos

| Archivo | Cambio |
|---|---|
| `frontend/src/features/participant/batch.ts` | Constantes, `addToBatch`, `dueAt`, `isDue`, `packBatch` y validación `isBatch`. |
| `frontend/src/features/participant/useBatch.ts` | Hook del lote: copia síncrona, contador de 250 ms, envío al vencer cuando se puede, «Enviar ahora» y persistencia. |
| `frontend/src/features/participant/BatchPreview.tsx` | Burbujas pendientes y barra con la cuenta regresiva (`role="timer"`) y «Enviar ahora». |
| `frontend/src/features/participant/AttemptChat.tsx` | Usa el lote; el campo y «Enviar» ya no se bloquean mientras Yummi responde; copia síncrona del borrador contra el doble envío. |
| `frontend/src/features/participant/useConversation.ts` | `submit` recibe los textos del lote y arma `messages` con `packBatch`; expone `idle`; `mergeHistory` conserva `parts`. |
| `frontend/src/features/participant/storage.ts`, `types.ts` | `loadBatch`/`saveBatch`, borrado del lote con la pulsera, `parts` opcional y validado en el historial. |
| `frontend/src/features/participant/chat.css` | Estilo de la burbuja pendiente y de la barra del lote. |
| `frontend/src/features/participant/AttemptChat.batch.test.tsx`, `batch.test.ts` | Pruebas nuevas del lote (8 y 5). |
| `frontend/src/features/participant/AttemptChat.test.tsx`, `AttemptChat.compose.test.tsx`, `storage.test.ts` | Pruebas existentes adaptadas a «Enviar ahora» y redacción durante la espera; reconciliación de `parts`; persistencia del lote. |
| `docs/dominio/frontend.md` | Sección «Mensajes en lote». |

## Cómo se verificó

- Desde `frontend/`: `pnpm install --frozen-lockfile`; `pnpm lint` (Biome, 112 archivos, sin errores); `pnpm typecheck` (`tsc -b`, sin errores); `pnpm test` con 29 archivos y 170 tests en verde (antes del cambio: 27 archivos y 154 tests); `pnpm build` en verde (180 módulos).
- `AttemptChat.batch.test.tsx` usa temporizadores falsos de Vitest (`setTimeout`, `setInterval` y `Date`) y cubre: espera de 10 s que se reinicia con un mensaje a los 9 s, tope a los 20 s con mensajes a los 0, 8 y 16 s, envío al cuarto mensaje, «Enviar ahora», unión con saltos de línea, división en `messages` con `message_max_length` de 10, lote siguiente que espera al intento en curso y sale con `continues`, lote lleno y recarga a los 4 s que envía a los 6 s restantes.
- Mutaciones a mano, revertidas: contar la espera desde el primer mensaje hace fallar 2 tests; enviar sin esperar al intento en curso hace fallar 1.
- No hubo revisión visual en navegador ni en teléfono; las pruebas son de DOM.

## Riesgos y efectos en otros frentes

- Sin cambios de backend ni de contrato: el POST ya aceptaba `messages` de 1 a 4 textos de hasta 4000 caracteres.
- Cada mensaje ahora tarda hasta 10 s en salir, salvo con «Enviar ahora» o al cuarto mensaje. En la Arena en vivo y en el monitor un lote aparece como un intento con un mensaje de varias líneas.
- `parts` es solo del navegador: otro dispositivo, o un historial que solo llega del servidor, muestra el lote como una burbuja con saltos de línea.
- Si el servidor rechaza el lote (422, o 404/409 de una conversación vencida), el texto unido vuelve al campo, como antes con un mensaje.

## Pendiente

- Revisión visual y de accesibilidad de la barra del lote en móvil.
