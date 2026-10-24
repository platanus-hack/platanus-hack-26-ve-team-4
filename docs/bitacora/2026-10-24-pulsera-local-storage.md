---
fecha: 2026-10-24
autor: "@franbastardo"
rama: fix/pulsera-local-storage
pr: 33
estado: en revisión
dominios: [frontend, sessions]
requisitos: []
---

# La pulsera del participante pasa a localStorage

## Qué cambió

La «pulsera» (token y datos de la sesión del participante) se guardaba en `sessionStorage`. Ahora se guarda en `localStorage`, igual que su historial pendiente. Cerrar la pestaña, abrir otra o reiniciar el navegador recupera la misma sesión: se valida contra `/api/sessions/me` y no se crea otra.

Cambios que `localStorage` hace necesarios:

| Caso | Comportamiento |
|---|---|
| Pulsera vencida | Al leerla se compara con `expires_at`; si venció se descarta. Antes moría con la pestaña. |
| Sesión invalidada (vencimiento o 401/403) | Se borra también su historial, para no acumular historiales de rondas viejas. |
| Pulsera guardada por la versión anterior | Si está en `sessionStorage`, se mueve a `localStorage` al leerla. Nadie pierde su sesión con el despliegue. |

## Por qué

Con `sessionStorage`, una persona que cerraba la pestaña perdía la pulsera, volvía a entrar con otro alias y creaba otra sesión. Cada sesión gasta cupo de la ronda (`AGENT_ZERO_ARENA_SESSION_LIMIT`) y una identidad sintética.

## Archivos

| Archivo | Cambio |
|---|---|
| `frontend/src/features/participant/storage.ts` | `localStorage`, descarte por vencimiento, borrado del historial al invalidar y migración desde `sessionStorage`. |
| `frontend/src/features/participant/storage.test.ts` | Persistencia al cerrar la pestaña, invalidación con historial, pulsera vencida y migración. |
| `docs/dominio/frontend.md` | Almacenamiento y recuperación de la sesión. |

## Cómo se verificó

- Frontend: 71 tests, `tsc -b`, Biome y build en verde.
- La prueba «conserva la pulsera al cerrar la pestaña» falla con la versión anterior: vacía `sessionStorage`, como una pestaña nueva, y espera recuperar la sesión.

## Riesgos y efectos en otros frentes

- Todas las pestañas del mismo navegador son el mismo participante. No hay botón de salir, así que dos personas en el mismo dispositivo compartirían identidad. En la demo cada persona entra desde su teléfono por el QR.
- Otro navegador o una ventana privada sí crean otra sesión: el servidor no puede distinguirlos.
- El secreto de operación no cambia: sigue sólo en memoria (`OperatorPage.test.tsx` lo verifica).

## Pendiente

- Si hiciera falta frenar sesiones desde otros navegadores, limitar del lado del servidor (por ejemplo, por IP).
