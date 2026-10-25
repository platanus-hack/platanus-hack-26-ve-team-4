---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: feat/chat-de-prueba
pr: pendiente
estado: en revisión
dominios: [sessions, live, arena, frontend]
requisitos: []
---

# Chat de prueba del equipo desde Operación

## Qué cambió

- `sessions/reserved_alias.py`: el prefijo `Interno-` queda reservado, como `Agente-`. `POST /api/sessions` solo lo acepta con el secreto de operador.
- `live/service.py`: las sesiones `Interno-` salen en el tablero con `kind: "test"`, sin enmascarar, y no cuentan en las KPI, `sessions_total`, `in_flight` ni campañas.
- `arena/scoring.py` y `arena_service.py`: `without_test_sessions` las saca de la clasificación y del conteo de la revelación.
- Frontend: Operación tiene la sección «Chat de prueba». El botón crea la sesión `Interno-<nombre o sufijo>` con el secreto, la guarda como la sesión del navegador y abre el chat del participante en otra pestaña. El tablero la rotula «Prueba interna».

## Cómo se verificó

- Backend (pasos 1 a 3, antes del rebase sobre `main` f99247e): en Docker, `tests/sessions` dio 26 passed y 1 skipped; `tests/live` dio 33 passed; `tests/arena/test_scoring.py` y `test_core_cycle.py` dieron 13 passed; mypy no encontró problemas en 684 archivos.
- Frontend (después del rebase): Biome revisó 118 archivos sin errores, `tsc -b` sin errores y Vitest de `features/operator` y `features/board` pasó 97 tests en 14 archivos.
- Modo de ajustes rápidos: la suite completa queda para la CI de `main`.

## Limitaciones

- Abrir el chat de prueba reemplaza la sesión de participante guardada en ese navegador.
- Cada chat de prueba ocupa una identidad sintética de la ronda (el cupo de sesiones).
