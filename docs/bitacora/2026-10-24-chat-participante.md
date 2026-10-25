---
fecha: 2026-10-24
autor: "@franbastardo"
rama: feat/chat-participante
pr: 47
estado: integrado
dominios: [frontend, attempts, victim]
requisitos: []
---

# La vista Participar pasa a ser el chat de soporte de Yummi

## Qué cambió

La pantalla del participante, una vez dentro, deja de ser un formulario de «intentos» con hasta cuatro turnos. Ahora es el chat de soporte de Yummi, el agente con el que la audiencia interactúa:

- **Ventana de chat** con cabecera de marca, burbujas, indicador «escribiendo…», sugerencias de consultas legítimas, Enter para enviar y «Nueva conversación».
- **Panel discreto «Laboratorio»** al costado (arriba en el teléfono, plegable). Contiene modo del proveedor, identidad ficticia, pedidos, objetivos, límites y el resultado provisional de cada mensaje. Los resultados ya no aparecen dentro del chat.
- **Cada mensaje es un intento.** El asistente ve la conversación en curso porque el backend admite `continues`, el intento anterior de la misma sesión.

Backend (`attempts/conversation.py`):

- Tabla nueva `attempt_links`, que entra en `ROUND_TABLES`.
- `continues` en `POST /api/attempts`, con validación de sesión (404), de intento terminado (409) y del máximo de 6 intentos por conversación (409).
- El historial y el detalle devuelven `continues`.
- `ConversationExecutor.start` antepone los turnos previos: mensajes con rol `user` y respuestas con rol `assistant`.

## Por qué

La audiencia entra por QR desde el teléfono y espera hablar con un chatbot, no llenar un formulario. Los ataques reales son de varios pasos, así que el bot tiene que recordar la conversación.

Decisiones de seguridad:

- **El historial lo arma el servidor.** El cliente solo manda el id del intento anterior, nunca el texto del historial: si lo mandara, podría inventar respuestas del asistente («ya verifiqué que eres el titular»).
- **Las herramientas de turnos previos no se repiten.** Un reembolso del mensaje anterior no se ejecuta otra vez.
- **Canarios redactados.** Las respuestas previas llegan al modelo como las vio el participante, con `[referencia]` en lugar del canario. La primera prueba lo detectó: la respuesta guardada trae el canario crudo, y repetirlo podía contar una filtración dos veces.
- **Procedencia sin cambios.** Solo cuenta lo que escribió el participante; la respuesta previa del asistente no da procedencia a ningún valor.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/src/agent_zero/attempts/conversation.py` | Nuevo: `chain`, `check_continuation`, `previous_turns`, `links_for`, `public_reply` y `MAX_PREVIOUS` |
| `backend/src/agent_zero/attempts/models.py` | `AttemptLink` |
| `backend/src/agent_zero/attempts/schemas.py` | `AttemptCreate.continues` |
| `backend/src/agent_zero/attempts/attempt_submission_service.py` | Valida y guarda el enlace; la idempotencia incluye `continues` |
| `backend/src/agent_zero/attempts/attempt_execution_handler.py`, `victim/tool_loop.py` | Turnos previos al iniciar la conversación |
| `backend/src/agent_zero/attempts/attempt_query_service.py`, `attempts/router.py` | `continues` en las vistas; `public_reply` reutilizada |
| `backend/src/agent_zero/arena/round_snapshot.py` | `attempt_links` en `ROUND_TABLES` |
| `backend/tests/arena/test_conversation.py` | Nuevo: el modelo ve los turnos previos (usuario, asistente, usuario) sin repetir herramientas; sesión ajena (404); idempotencia con `continues`; largo máximo |
| `frontend/src/features/participant/useConversation.ts` | Nuevo: la lógica de envío durable que vivía en `AttemptChat`, más conversaciones y `continues` |
| `frontend/src/features/participant/AttemptChat.tsx`, `chat.css` | Interfaz de chat |
| `frontend/src/features/participant/LabPanel.tsx` | Nuevo: panel del laboratorio |
| `frontend/src/features/participant/ParticipantPage.tsx`, `types.ts`, `storage.ts` | Encabezado compacto y `continues` en tipos y almacenamiento |
| `frontend/src/features/participant/AttemptChat.test.tsx` | Adaptado a la interfaz nueva. Los cuatro turnos explícitos se reemplazan por «Nueva conversación» y por el rechazo de una continuación |
| `docs/dominio/attempts.md`, `docs/dominio/frontend.md` | Contrato de `continues` y comportamiento del chat |

## Cómo se verificó

- Backend:
  - `tests/arena/test_conversation.py`: 3 passed;
  - `tests/arena`, `tests/victim`, `tests/attempts` y `tests/test_traceability.py`: 178 passed, 21 skipped;
  - `ruff check`, `ruff format --check` y `mypy src tests` limpios (629 archivos).
- Frontend:
  - `pnpm lint`, `pnpm typecheck`, `pnpm test` (97 pruebas) y `pnpm build` en verde;
  - las pruebas de `src/features/participant` pasaron 8 de 8 corridas seguidas.
- Prueba HTTP contra un backend `demo` con datos nuevos: un mensaje sobre el pedido propio y otro que lo continúa. El segundo devuelve `continues` igual al id del primero y obtiene respuesta.
- Falta la revisión visual en navegador y en teléfono [SUPUESTO: solo se comprobó el DOM con jsdom].

## Riesgos y efectos en otros frentes

- **Validación de parches:** `validation_cases` y la repetición del operador usan `attempt.messages`, sin la conversación previa. Un ataque que solo funciona con contexto puede no reproducirse al validar el parche. [SUPUESTO] No se probó con un ataque real de varios mensajes.
- **Base existente:** `attempt_links` se crea sola al arrancar; los intentos anteriores quedan sin enlace, como conversaciones de un solo mensaje.
- **Señuelo:** una sesión desviada sigue su conversación dentro del señuelo; el historial viene de sus propios intentos.
- **Clientes de la API:** `messages` con varios turnos sigue funcionando (Prober y evaluación no cambian); el chat manda uno por intento.

## Pendiente

- Llevar la conversación previa a la validación y a la repetición de parches cuando el ataque dependa del contexto.
- Revisión visual en un teléfono real contra un despliegue.
