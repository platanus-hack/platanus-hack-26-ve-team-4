---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: fix/chat-envio-directo
pr: pendiente
estado: en revisión
dominios: [frontend]
requisitos: []
---

# El chat envía en el momento, con tope de 10 mensajes sin respuesta

## Qué cambió

- Se quitó la espera visible del lote: ya no hay «Pendiente», «Se envía en N s» ni «Enviar ahora». Cada mensaje sale al apretar «Enviar».
- Lo escrito mientras Yummi responde queda en una cola, se ve como enviado y sale junto en el intento siguiente. Eso sigue siendo necesario porque el servidor admite una sola ejecución pendiente por sesión.
- Regla nueva: con 10 mensajes sin respuesta (`QUEUE_MAX`), «Enviar» se desactiva y el chat pide esperar unos segundos a que Yummi responda.
- Se quitó el aviso «Yummi está respondiendo…» del campo; el encabezado sigue diciendo «Escribiendo…».

## Cómo se verificó

- Biome revisó 118 archivos sin errores y `tsc -b` no dio errores.
- Vitest de `features/participant`: 43 tests en 7 archivos, en verde.
- Modo de ajustes rápidos: la suite completa queda para la CI de `main`.
