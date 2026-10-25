---
fecha: 2026-10-25
autor: "carlos sanoja"
rama: main
estado: integrado
dominios: [sessions, victim, frontend]
---

# Identidad de la sesión igual al nombre de sus pedidos, y Yummi

## Qué cambió

- La sesión del participante devuelve como `customer_name` el mismo nombre ficticio que figura en sus pedidos (por ejemplo, **Luis García**), en `POST /api/sessions` y en `GET /api/sessions/me`. Antes devolvía una etiqueta armada con el ID (`Demo-0082`).
- La víctima recibe `cliente_autenticado` con ese nombre, junto a `memoria_no_confiable`, al empezar cada conversación.
- `customer_name_of()` en `victim/fixtures.py` es la única fuente de ese nombre.
- La marca del asistente pasa de "Yummy" a "Yummi" en código, contrato, base de conocimiento, frontend y documentación. Quedan sin cambios las evidencias de `artifacts/` (tienen checksum) y el nombre oficial del evento.

## Por qué

Una prueba con 10 usuarios simulados contra el modo `live` mostró que, desde que los pedidos traen nombre, el panel y los pedidos no coincidían. El participante se presentaba con su alias, el modelo veía otro nombre en su pedido y concluía que era de otra persona. Ocurrió en 2 de 9 sesiones: negó el servicio sobre pedidos propios, reveló el nombre del titular y se contradijo.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/src/agent_zero/victim/fixtures.py` | `customer_name_of()` |
| `backend/src/agent_zero/sessions/router.py` | `customer_name` sale de `customer_name_of()` |
| `backend/src/agent_zero/victim/tool_loop.py` | `cliente_autenticado` en la cabecera de la conversación |
| `backend/tests/sessions/test_router.py` | La identidad de la sesión coincide con sus pedidos |
