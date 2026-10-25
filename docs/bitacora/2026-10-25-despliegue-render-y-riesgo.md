---
fecha: 2026-10-25
autor: "@CarSanoja"
rama: main
pr: ninguno  # push directo a main
estado: integrado
dominios: [routing, victim, memory_bank, infra, frontend]
requisitos: [CORE-06, MEM-03]
---

# Puntuación de riesgo, integración de la Arena en vivo y despliegue en Render

## Qué cambió

- El desvío al señuelo usa una puntuación de riesgo por sesión en una ventana de 10 minutos, con umbral 6, en lugar de tres denegaciones seguidas ([routing](../dominio/routing.md#puntuación-de-riesgo)).
- Cuando un pedido no se puede usar, el modelo recibe una indicación neutra: pedir al cliente que revise el número, sin revelar si existe ni de quién es.
- Se integraron los PR #50 y #51 (Arena en vivo con chats desplazables) en `71273fa`; el único conflicto fue de estilos.
- El despliegue público corre en Render desde `render.yaml`, con Postgres 17, backend privado con disco y web pública: https://agent-zero-yt2m.onrender.com.
- El backend acepta la URL `postgres://` del proveedor y deriva la clave de memoria del secreto que genera Render.
- La `deploy-url` del proyecto y el README apuntan al despliegue.

## Por qué

- En la prueba manual, un participante escribió un número de pedido inexistente y el sistema contó esa denegación igual que un intento sobre un pedido ajeno. Tres errores de tecleo bastaban para mandar a un cliente honesto al señuelo, y un atacante evitaba el desvío intercalando consultas legítimas.
- Desviar a un honesto le entrega datos falsos de sus propios pedidos; dejar a un atacante en el entorno protegido no filtra nada. Por eso el desvío exige evidencia acumulada.

## Archivos

- `backend/src/agent_zero/routing/session_risk.py`, `session_risk_reader.py` y `route_decision_service.py`, más `events/event_store.py` y `config.py`.
- `backend/src/agent_zero/victim/denial_view.py` y `tool_loop.py`.
- `backend/src/agent_zero/memory_bank/memory_cipher.py`.
- `render.yaml`, `frontend/nginx/15-backend-url.envsh`, `frontend/Dockerfile` y `docs/despliegue.md`.
- `README.md` y `platanus-hack-project.jsonc`.

## Cómo se verificó

- **Puntuación de riesgo.** Hay pruebas unitarias del puntuador (tecleo, pedidos ajenos, enumeración intercalada) y dos recorridos completos:
  - un honesto que teclea mal cuatro veces sigue en el entorno protegido;
  - un atacante que enumera intercalando consultas propias termina en el señuelo con motivo `risk_score`.
- **Suites:**
  - backend contra Postgres: 1347 aprobadas y 4 omitidas;
  - backend en SQLite tras los cambios de Render: 1329 aprobadas;
  - frontend tras la integración: 154 pruebas, más `pnpm typecheck`, build y Biome.
- **Imagen de nginx:** en local, con `PORT=10000` y `BACKEND_HOSTPORT`, resolvió el proxy y respondió `healthz` 200.
- **Render:**
  - el backend creó sus bases y arrancó en 17 s;
  - `infra/scripts/smoke.py https://agent-zero-yt2m.onrender.com` aprobó frontend, readiness, SPA, estado público, autorización y proxy SSE;
  - dos sesiones de humo (`humo-render`, `humo-render-2`) completaron intentos, y el ataque a un pedido ajeno activó la política v1 en modo demo.

## Riesgos y efectos en otros frentes

- La cuenta de Render es el workspace asociado a `csanoja@somosquanta.com`.
- La ronda de producción contiene dos sesiones de humo; hay que reiniciarla desde Operación antes del evento.
- `autoDeploy` está desactivado: cada cambio en `main` necesita un despliegue manual.
- La clave de Anthropic configurada se expuso en el chat; debe rotarse antes de pasar a `live`.

## Pendiente

- Rotar la clave y pasar a `live` con tope diario.
- Prueba de carga contra Render.
- Cerrar el PR #51, cuyo contenido ya está en `main`.
