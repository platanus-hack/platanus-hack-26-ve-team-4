---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: feat/barra-al-salir
pr: pendiente
estado: en revisión
dominios: [frontend]
requisitos: []
---

# La barra de navegación vuelve al salir de la Arena en vivo

## Qué cambió

Antes, `/arena` ocultaba la barra de navegación por la ruta. Al tocar «Salir» dentro de la Arena, el secreto se borraba y aparecía otra vez el formulario «Secreto de operador», pero la barra seguía oculta porque la ruta seguía siendo `/arena`: no había forma de ir a Participar, Monitor u Operación sin escribir la URL.

Ahora la barra se oculta solo mientras `LiveArena` está montada con el secreto:

- `App` guarda `projecting` (`useState`) y lo pasa a `Navigation` como `hidden`.
- `BoardPage` acepta la prop opcional `onProjectingChange` y la pasa a `LiveArena`.
- `LiveArena` avisa `true` al montarse y `false` al desmontarse. «Salir» desmonta `LiveArena` a través de `OperatorGate`, y un 401 hace lo mismo con `logout`; en ambos casos la limpieza devuelve la barra.

En el acceso (sin secreto) la barra se ve junto al formulario. Con el secreto aceptado, la Arena se proyecta a pantalla completa como antes.

## Por qué

Pedido de Fernando: la Arena en vivo se proyecta, pero al salir de ella tiene que poder moverse a otros espacios sin editar la URL.

## Archivos

| Archivo | Cambio |
|---|---|
| `frontend/src/app/App.tsx` | `Navigation` recibe `hidden` en lugar de mirar la ruta; `App` guarda `projecting`. |
| `frontend/src/features/board/BoardPage.tsx` | Prop opcional `onProjectingChange`; `LiveArena` la llama al montarse y al desmontarse. |
| `frontend/src/app/App.test.tsx` | Prueba de `/arena` en el acceso (la barra se ve) y prueba nueva de entrar con el secreto (la barra se oculta) y de «Salir» (la barra vuelve). |
| `docs/dominio/tablero.md` | Viñeta «Ruta y acceso» de la sección Frontend. |
| `docs/bitacora/2026-10-25-barra-al-salir.md` | Esta bitácora. |

`BoardPage.test.tsx` no cambió y sigue pasando sin props.

## Cómo se verificó

Desde `frontend/` del worktree `wt-barra-al-salir`:

- `pnpm install --frozen-lockfile`: dependencias instaladas.
- `pnpm exec biome check --vcs-root=.. .` (lint): 112 archivos revisados, sin errores. Biome marcó orden de imports en `App.test.tsx` y formato en `BoardPage.tsx`; se corrigieron con `biome check --write` sobre esos dos archivos antes del commit.
- `pnpm typecheck` (`tsc -b`): sin errores.
- `pnpm exec vitest run src/app/App.test.tsx src/features/board/BoardPage.test.tsx`: 2 archivos, 10 tests en verde (antes del formato de Biome).
- `pnpm test`: 29 archivos y 171 tests en verde. La bitácora de `chat-mensajes-en-lote` registró 170 tests en la base; el número base no se volvió a medir en esta rama, así que el delta de +1 es el test nuevo de App.
- `pnpm build`: `tsc -b && vite build` en verde; `dist/assets/index-ByBfii-h.js` 378.88 kB (gzip 119.36 kB).

## Riesgos y efectos en otros frentes

- Solo cambia la visibilidad de la barra. Sin cambios de backend, de rutas ni de contrato.
- El aviso `onProjectingChange` depende de que `App` pase `setProjecting`, que es estable. Si alguien pasa una función nueva en cada render, el efecto se reejecutaría, aunque el valor final sería el mismo.
- La ruta 401 (secreto vencido durante el polling) usa la misma limpieza, pero la prueba nueva cubre solo «Salir». El 401 no tiene prueba propia todavía.

## Pendiente

- Prueba de la vuelta de la barra tras un 401 en `App.test.tsx`.
- Revisión visual en pantalla de proyección y en móvil de la barra al salir.
