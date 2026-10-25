---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: feat/limite-240-por-minuto
pr: pendiente
estado: en revisión
dominios: [attempts, llm, agent-gateway, infraestructura]
requisitos: []
---

# El límite de intentos por minuto sube de 12 a 240

## Qué cambió

- `arena_attempts_per_minute` pasa de 12 a 240 intentos por minuto y sesión. El valor llega al participante en `limits.attempts_per_minute` y el chat lo muestra como «Límite: 240 mensajes por minuto».
- `llm_session_call_limit` pasa de 40 a 400 llamadas al modelo por sesión. Es un tope sin ventana que se acumula durante toda la sesión.
- `gateway_rate_limit_per_minute` pasa de 60 a 480 llamadas por minuto y agente. La clave del limitador es `agente:escenario`.
- `render.yaml`, `.env.example` y `infra/compose.yaml` reflejan los nuevos valores. Compose añade `AGENT_ZERO_ARENA_ATTEMPTS_PER_MINUTE` con 240 por defecto.
- El enjambre de pruebas (`backend/scripts/attack_swarm.py`) conserva su espaciado de 5,2 s y su comentario apunta al nuevo cupo.

No cambian `arena_session_queue_limit` (1), `arena_queue_limit` (40 en base, 120 en Render), `llm_daily_call_limit`, `llm_daily_usd_limit` ni el lote del chat del participante.

## Por qué

Fernando pidió subir el límite de 12 a unos 200–300 mensajes por minuto, porque una persona puede generar fácilmente ese ritmo. Se eligió 240. Antes de cambiarlo se revisaron los topes relacionados:

1. **Tope de llamadas por sesión.** En la evaluación LIVE hubo 683 llamadas del rol `victim` en 270 ejecuciones, unas 2,5 por ejecución ([evaluación LIVE y costes](2026-10-24-evaluacion-live-costes.md)). Con 40 llamadas, una persona quedaba cortada a unos 16 intentos y el 240 no tenía efecto real. Con 400 llamadas quedan unos 160 intentos por sesión. El coste medido es de 0,0000941 US$ por llamada, así que 400 llamadas cuestan unos 0,04 US$ por sesión. Los topes diarios no cambian: 5000 llamadas al día equivalen a unos 0,47 US$ y el límite de US$2 sigue vigente.
2. **Límite del gateway.** Con 60 llamadas por minuto, la evaluación LIVE ya registró denegaciones `rate_limited` en la traza de herramientas ([traza v2](2026-10-24-traza-herramientas-v2.md)). Con 240 intentos y [SUPUESTO] unas 2 herramientas por intento, hacen falta unas 480 llamadas por minuto. Por eso el límite pasa a 480. Esas denegaciones no suman riesgo, pero degradan las respuestas.
3. **Cola por sesión.** Se mantiene en 1. El chat espera a que termine la respuesta anterior antes de mandar el siguiente lote, y la continuidad de la conversación depende de ese orden.
4. **Cola global.** No cambia. Es un límite por origen, no por sesión.
5. **Lote del chat.** No cambia: 10 s sin escribir, 20 s como máximo y 4 mensajes por lote. Con una ejecución pendiente por sesión y una mediana de 2,88 s por ejecución (LIVE, política 0), una persona real queda muy por debajo de 240. El límite solo corta a quien usa «Enviar ahora» o el modo demo.

## Archivos

- `backend/src/agent_zero/config.py`: valores por defecto de los cuatro topes.
- `backend/tests/arena/test_attempt_limits.py`: el test de ventana deslizante fija 12 para conservar sus marcas de tiempo. Dos tests nuevos comprueban el valor por defecto de 240, que llega al participante, y los topes relacionados.
- `backend/tests/sessions/test_router.py`: la respuesta de `POST /api/sessions` esperaba 12 con la configuración por defecto; ahora espera 240.
- `backend/scripts/attack_swarm.py`: comentario del cupo, en dos líneas para cumplir el límite de 100 caracteres.
- `.env.example`, `infra/compose.yaml`, `render.yaml`: nuevos valores.
- `docs/dominio/attempts.md`, `docs/dominio/rendimiento.md`, `docs/dominio/tablero.md`: cifras actualizadas.

## Cómo se verificó

- `ruff check .`: All checks passed!
- `ruff format --check .`: 697 files already formatted.
- `pytest -q tests/arena/test_attempt_limits.py tests/llm tests/agent_gateway tests/live tests/sessions/test_router.py` en Docker `python:3.12-slim-bookworm`: 187 passed, 2 skipped, en 70,58 s. Antes del último commit de pruebas, `test_attempt_limits.py` y `test_router.py` pasaron con 7 tests.
- `mypy src tests scripts` en Docker: Success: no issues found in 683 source files.
- Ningún test de `tests/llm`, `tests/agent_gateway` ni `tests/live` dependía del 40 ni del 60 por defecto. Los que tocan el gateway o el LLM fijan sus valores (3 en `tests/agent_gateway/conftest.py`, 10000 en `tests/live/conftest.py`, 1000 en `tests/arena/conftest.py`).

## Riesgos

- Un `.env` local copiado del ejemplo anterior conserva `AGENT_ZERO_LLM_SESSION_CALL_LIMIT=40`. Hay que actualizarlo a 400 y reiniciar el backend. Compose no define `AGENT_ZERO_ARENA_ATTEMPTS_PER_MINUTE` en ese caso, así que toma el 240 por defecto.
- Render toma los valores de `render.yaml` solo al sincronizar el Blueprint. Hay que sincronizarlo para que la instancia en línea use 240 y 400.
- Las cifras de coste son estimaciones con tokens medidos, no una factura del proveedor.

## Pendiente

- Medir en la arena real cuántas herramientas usa un intento, para confirmar el supuesto de 2 herramientas por intento y el tope de 480.
- Confirmar con Fernando el valor de 240 antes de sincronizar el Blueprint de Render.
