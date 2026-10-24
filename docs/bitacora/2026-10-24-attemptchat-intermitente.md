---
fecha: 2026-10-24
autor: "@franbastardo"
rama: horda/attemptchat-tests-estables-integracion
pr: pendiente
estado: en revisión
dominios: [frontend, attempts]
requisitos: []
---

# Pruebas de AttemptChat estables: esperar las dos fuentes y fijar el reloj en los 429

## Qué cambió

- «cierra envío al pausar y mantiene el historial visible» espera con `findByText` el aviso de pausa y también «Solicitud rechazada.», y comprueba que el campo de mensaje queda deshabilitado.
- Las dos pruebas de 429 fijan `Date.now` con `vi.spyOn` antes del envío. Comprueban el texto exacto «Reintentar en 60 s» y «Reintentar en 5 s» con `findByRole`. Antes aceptaban 60|59 y 5|4. La de 5 s también comprueba que se conserva la clave.
- `AttemptChat.tsx` no cambia.

## Por qué

El aviso de pausa viene de `useArenaState` (`GET /api/arena/state`, cada 2000 ms). El historial viene de `usePolling` (`GET /api/attempts`, cada 1500 ms). Son dos peticiones independientes. La prueba usaba `getByText` síncrono para la segunda, así que fallaba cuando la arena se pintaba antes. Se reprodujo en 3 de 6 corridas en paralelo.

En los 429, la cuenta atrás depende del reloj real: `ceil((retryAt - Date.now())/1000)`, con un intervalo de 500 ms. Bajo carga, el texto podía pasarse del rango que aceptaba la regex.

No se usaron temporizadores falsos. Interfieren con `userEvent` y con el `setTimeout` de `usePolling`.

[SUPUESTO] La causa del fallo del 429 en CI es la carga de la máquina. Localmente no se reprodujo.

## Archivos

- `frontend/src/features/participant/AttemptChat.test.tsx`

## Cómo se verificó

Desde `frontend/`, el 2026-10-24, en la rama integrada (commits `ff4c7b9`, `f88dd85` y `1a975eb`):

- Bucle de 15 corridas de `pnpm exec vitest run src/features/participant/AttemptChat.test.tsx`: 15 de 15 en verde, 12 pruebas pasadas en cada una.
- 6 corridas en paralelo del mismo archivo: 6 de 6 en verde, 12 pruebas pasadas en cada una.
- `pnpm lint`: Biome revisó 86 archivos sin errores. `pnpm typecheck`: sin errores. `pnpm test`: 21 archivos y 96 pruebas pasadas.
- `git diff --stat -- src/features/participant/AttemptChat.tsx`: vacío. El componente no cambia.

## Riesgos y efectos en otros frentes

Ninguno en producción. Solo cambian las pruebas.

## Pendiente

- Revisar si otras pruebas que combinan `useArenaState` con otro poll (ArenaPage, RevealCard, GuardPanel) usan `getBy` síncrono después de un `findBy` de la otra fuente.
