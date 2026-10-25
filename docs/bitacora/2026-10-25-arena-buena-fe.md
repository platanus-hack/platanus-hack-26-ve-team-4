---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: feat/arena-buena-fe
pr: pendiente
estado: en revisión
dominios: [frontend]
requisitos: []
---

# La Arena en vivo presume buena fe al Público

## Qué cambió

Antes, `chatStatus` devolvía «Atacando» para toda sesión sin desenlace: el chat enmascarado («Atacando · Oculto hasta revelar»), el que no tenía intentos terminados («Atacando · Primer intento») y el de respaldo («Atacando · Último: no logrado»). Las burbujas de cada intento se rotulaban «Atacante», el KPI «Ataques» y el carrusel vacío «Esperando atacantes…».

Ahora:

| Sesión | Sin evidencia | Con evidencia |
|---|---|---|
| Público (`audience`) | «Conversando · Oculto hasta revelar»; «Conversando · Primer mensaje»; «Conversando · Sin señales de riesgo» | «Señal de riesgo · pedido ajeno · intento N» (una negación de validador; `rate_limited` y `order_exists` no cuentan) |
| Enjambre y Prober (`swarm`, `prober`) | «Atacando · Primer intento» o «Atacando · Último: …» | Igual que antes |

«Se filtró», «En espacio seguro», «Bloqueado» y «Acceso cerrado» no cambian. El tono interno «attacking» pasó a «neutral» (su color ya era neutro). Las burbujas dicen «Participante» para el Público y «Atacante» para el enjambre y el Prober. El KPI se llama «Intentos» y el carrusel vacío dice «Esperando participantes…».

## Por qué

Pedido de Fernando: no toda persona es un atacante. Se presume buena fe a quien escribe en el Público, y el lenguaje de ataque solo aparece con evidencia del sistema o para los agentes que atacan por diseño.

## Archivos

| Archivo | Cambio |
|---|---|
| `frontend/src/features/board/status.ts` | Reglas de buena fe en `chatStatus`, `speakerLabel` y la señal de riesgo (`isRiskDenial`). |
| `frontend/src/features/board/status.test.ts` | Nuevo: casos de buena fe, señal de riesgo, enmascarado, filtrado y rótulos. |
| `frontend/src/features/board/types.ts` | Tono `neutral` en lugar de `attacking`; comentario de las etiquetas de `ChatStatus`. |
| `frontend/src/features/board/ChatTile.tsx`, `ChatTile.test.tsx` | Burbujas con `speaker`; prueba de «Participante» y «Atacante». |
| `frontend/src/features/board/KpiColumn.tsx`, `KpiColumn.test.tsx` | KPI «Intentos». |
| `frontend/src/features/board/Carousel.tsx`, `Carousel.test.tsx` | Carrusel vacío «Esperando participantes…»; tono `neutral`. |
| `frontend/src/features/board/chat.css`, `carousel.css`, `stage.css` | Clases `st-neutral`; comentario de `--neutral`. |
| `frontend/src/features/board/slots.test.ts` | Tono `neutral`. |
| `docs/dominio/tablero.md` | Franjas de estado, regla de buena fe, rótulos y KPI. |

## Cómo se verificó

Desde `frontend/` del worktree `feat/arena-buena-fe`:

- `pnpm install --frozen-lockfile`: sin cambios en el lockfile.
- `pnpm lint` (Biome, `biome check .`): 113 archivos, sin errores.
- `pnpm typecheck` (`tsc -b`): sin errores.
- `pnpm test` (Vitest): 30 archivos y 180 tests en verde. Antes del cambio: 29 archivos y 170 tests. `status.test.ts` agrega 9 tests y `ChatTile.test.tsx` agrega 1.
- `pnpm build`: 180 módulos transformados, build en verde.
- `git grep -n attacking -- frontend`: sin resultados.
- `git log origin/main..HEAD --format=%B | grep -ci co-authored`: 0.

## Riesgos y efectos en otros frentes

- Solo cambia el frontend. El backend no manda etiquetas (`live/service.py` solo manda códigos), así que no hay cambios de contrato.
- Un Público revelado sin negaciones ya no aparece como «Atacando»; quien mire el tablero ve «Conversando». Esto es intencional.
- La prueba `AttemptChat.test.tsx` («envía con token y clave estable…») superó el tiempo de 5 s una vez en la corrida completa, con carga de la suite. Pasó sola (14 de 14) y en las corridas completas siguientes (180 de 180). No toca el código de la Arena; queda como posible prueba lenta.
- Los textos de «Ataque» en `docs/dominio/tablero.md` que describen al participante como «atacante» (líneas 51 y 61) se dejaron como están, fuera de este encargo.

## Pendiente

- Revisión visual de las franjas y las burbujas con datos reales en el tablero.
