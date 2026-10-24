# Frontend: participante, arena y operación

Estado: implementación revisada sobre la base funcional `1d0e21d`. React y TypeScript consumen la API del mismo origen. Las autorizaciones, resultados y puntuaciones se resuelven en el servidor; los estados visuales no sustituyen esos controles.

## Entradas y separación de responsabilidades

| Entrada | Función |
| --- | --- |
| [App.tsx](../../frontend/src/app/App.tsx) | Rutas `/` de participante, `/arena` pública y `/operator` reservada. |
| [ParticipantPage.tsx](../../frontend/src/features/participant/ParticipantPage.tsx) | Consentimiento, alta y recuperación mediante `/api/sessions/me`. |
| [AttemptChat.tsx](../../frontend/src/features/participant/AttemptChat.tsx) | Edición de hasta cuatro mensajes, envío durable y reconciliación del historial. |
| [storage.ts](../../frontend/src/features/participant/storage.ts) | Sesión e historial pendiente en `localStorage`, con validación al leer; descarta la pulsera vencida y migra la que haya quedado en `sessionStorage`. |
| [ArenaPage.tsx](../../frontend/src/features/arena/ArenaPage.tsx) | Estado agregado, cronómetro transcurrido, actividad SSE, QR y clasificación. |
| [OperatorPage.tsx](../../frontend/src/features/operator/OperatorPage.tsx) | Controles, campañas, políticas, hallazgos, evaluación y reset archivado. |
| [MonitorPage.tsx](../../frontend/src/features/monitor/MonitorPage.tsx) | Panel de la empresa en `/monitor`: KPIs de la ronda, feed de intentos con filtros, detalle con conversación y grafo, y tendencias (violación por versión, versiones de política, tokens por intento). |
| [http.ts](../../frontend/src/shared/api/http.ts) | Errores tipados, timeout, cancelación y lectura de `Retry-After`. |
| [usePolling.ts](../../frontend/src/shared/api/usePolling.ts) | Consultas seriales y descarte de respuestas de un propietario anterior. |

Los contratos se declaran junto a cada feature, en [participant/types.ts](../../frontend/src/features/participant/types.ts), [arena/types.ts](../../frontend/src/features/arena/types.ts) y [operator/api.ts](../../frontend/src/features/operator/api.ts). Cambiar un payload exige revisar esos tipos y las pruebas del consumidor correspondiente.

## Flujo del participante y fallos de red

Al recargar, cerrar la pestaña o abrir otra, se recupera el token del navegador (`localStorage`) y se valida contra `/api/sessions/me`; no se crea otra identidad ni se gasta otro cupo de la ronda. Todas las pestañas del mismo navegador son el mismo participante. Otro navegador o una ventana privada sí crean otra sesión: el servidor no puede distinguirlos. Un 401/403 invalida la sesión local. Un fallo de transporte conserva el token y permite volver a consultar.

Antes del POST se guarda una entrada con mensajes exactos y una clave aleatoria generada mediante `crypto.getRandomValues`, que funciona en HTTP local. La clave se conserva si se pierde la respuesta, incluso tras recargar. El historial consultado al servidor se reconcilia por ID o `idempotency_key`; una aceptación ya existente evita enviar de nuevo.

La interfaz bloquea envíos simultáneos y nuevos envíos mientras existe una entrada pendiente. Un 422 permite corregir el formulario; un 429 conserva la clave y respeta `Retry-After`. Las mutaciones no se reintentan silenciosamente desde el cliente HTTP.

Los límites vienen de la sesión, con compatibilidad de campos anterior. La UI muestra pausa de admisión y resultados provisionales. Tras revelar, vuelve a leer el resultado final propio; una lectura antigua no puede convertir una respuesta terminal en un intento en cola.

## Arena y operación

`usePolling` usa por defecto 2 s entre consultas completadas; el historial del chat usa 1,5 s. No solapa una lectura lenta con la siguiente y aborta/desestima respuestas al cambiar credenciales, ronda o componente. Ante errores conserva los últimos datos y muestra que pueden estar desactualizados.

[useArenaEvents.ts](../../frontend/src/features/arena/hooks/useArenaEvents.ts) utiliza `EventSource`, valida tipo/visibilidad/ID, deduplica y conserva hasta 100 eventos recientes. La reconexión de la misma instancia usa el comportamiento nativo de `EventSource`; los contadores completos vienen de `/api/arena/state`.

La repetición del ataque vive en [replay/](../../frontend/src/features/arena/replay/). `useReplay` espera un `patch_validated` con `passed=true`, consulta `GET /api/arena/replay/{version}` y `ReplayStage` dibuja dos columnas (política anterior con el efecto en rojo, política nueva con la arista cortada y «bloqueado por política vN») y la fila de tareas legítimas. `AttackGraph` es SVG puro con texto además de color; con `prefers-reduced-motion` salta al estado final. Si la ruta responde 404 no se muestra nada. Muestra el rótulo «repetición de las llamadas a herramientas registradas»: el «antes» sale de la traza original y no se vuelve a ejecutar.

El panel de [monitor/](../../frontend/src/features/monitor/) usa el mismo secreto de operador en memoria y consulta `GET /api/operator/monitor` y `/api/operator/policies` cada 4 s. El detalle pide `GET /api/operator/attempts/{id}` y dibuja `graph` con `AttackGraph`. Si el intento es una violación cuyo parche tiene repetición, muestra la pantalla dividida de `/api/arena/replay/{version}` con las tareas legítimas. Las violaciones por versión cuentan sólo la ruta protegida con veredicto. Sin llamadas LIVE, los tokens se muestran como «sin medir» y el coste como «simulado».

[JoinCode.tsx](../../frontend/src/features/arena/JoinCode.tsx) genera SVG local con `qrcode`. Acepta HTTP/HTTPS sin usuario ni contraseña y normaliza el enlace a la raíz del origen. Usa `VITE_PUBLIC_PARTICIPANT_URL` de build o el origen actual; también se puede editar en la tarjeta. Ese cambio no publica un despliegue.

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
pnpm exec vitest run src/features/arena src/shared/api
```

| Archivos de pruebas | Comportamiento cubierto |
| --- | --- |
| [ParticipantPage.test.tsx](../../frontend/src/features/participant/ParticipantPage.test.tsx), [storage.test.ts](../../frontend/src/features/participant/storage.test.ts) | Consentimiento, alta, recuperación, expiración/reset, JSON corrupto y almacenamiento no disponible. |
| [AttemptChat.test.tsx](../../frontend/src/features/participant/AttemptChat.test.tsx) | Respuesta perdida, recarga, reconciliación sin duplicar, cuatro turnos, doble envío, frecuencia y revelación sin filtrar ruta. |
| [OperatorPage.test.tsx](../../frontend/src/features/operator/OperatorPage.test.tsx) | Autorización, secreto no persistido, acciones seriales, evidencia, reset y evaluación explícita. |
| [ArenaPage.test.tsx](../../frontend/src/features/arena/ArenaPage.test.tsx), [useArenaEvents.test.ts](../../frontend/src/features/arena/hooks/useArenaEvents.test.ts) | Modo simulado, marcador, QR, eventos privados/malformados, duplicados y cambio de ronda. |
| [http.test.ts](../../frontend/src/shared/api/http.test.ts), [usePolling.test.ts](../../frontend/src/shared/api/usePolling.test.ts) | Timeout/cancelación, `Retry-After`, datos previos, ausencia de solapamiento y respuestas antiguas. |

La ejecución previa aprobó 47 pruebas, lint, TypeScript y build. El proxy y el ejercicio completo se verificaron con imágenes Docker reales. Esas verificaciones son DOM/HTTP; no hubo revisión visual de navegador disponible. La [guía de evidencias](../pruebas/evidencias.md) conserva la diferencia.

## Qué completar después

El backend emite `round_started`, pero el tipo y la suscripción del frontend todavía no lo incluyen: el polling de estado detecta el nuevo `round_id` y reinicia la conexión. Añadir el evento debe conservar la separación de rondas y el descarte de conexiones antiguas.

La UI de reset muestra el `archive_id`; listar y descargar archivos de rondas previas sigue siendo una operación de API. Falta revisión visual y de accesibilidad en móvil/navegador, además de QR desde un teléfono contra un despliegue publicado. Al ampliar un flujo, mantener el estado de recuperación, la idempotencia y los tests de respuestas tardías antes de modificar la presentación.
