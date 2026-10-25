---
fecha: 2026-10-24
autor: "@CarSanoja"
rama: main
pr: ninguno  # push directo a main
estado: integrado
dominios: [agent_gateway, attempts, loadtest, docs]
requisitos: [GW-02]
---

# Experimento en vivo, control de honestos y corrida en frío

## Qué cambió

- `backend/scripts/corrida_en_frio.py`: guion de la corrida en frío con dos participantes simulados.
- `docs/pruebas/experimento-arena-en-vivo.md`: objetivo, fases, hipótesis H1-H6, métricas, control y resultados de la corrida en frío.
- `backend/src/agent_zero/loadtest/control.py`: control de participantes honestos con duración fija e informe de bloqueos falsos y desvíos al honeypot por versión de política.
  - `participant.py` gana `Persona` y un plazo en `Pace`.
  - `operator_api.py` reúne la lectura del operador.
- `agent_gateway/policy_engine.py` y `agent_gateway.py`: con contexto de arena, el límite por minuto se cuenta por sesión (`agente:sesión`). Sin contexto se cuenta por agente, como antes.
- `attempts/schemas.py`: un mensaje formado solo por espacios o caracteres de formato invisibles (`Cf`) se rechaza como vacío.

## Por qué

En la corrida en frío LIVE, 23 de 54 intentos honestos acabaron en el honeypot mientras 20 atacantes usaban la arena. Todos los participantes comparten un agente, así que el tope de 60 llamadas por minuto se agotaba para todos. Las consultas legítimas recibían `rate_limited`, y tres denegaciones seguidas desvían la sesión al señuelo. En el evento eso habría mandado a público honesto al honeypot.

## Archivos

- `backend/src/agent_zero/agent_gateway/policy_engine.py`, `backend/src/agent_zero/agent_gateway/agent_gateway.py`, `backend/tests/agent_gateway/test_policy_engine.py` y `backend/tests/agent_gateway/test_agent_gateway.py`.
- `backend/src/agent_zero/attempts/schemas.py` y `backend/tests/attempts/test_schemas.py`.
- `backend/src/agent_zero/loadtest/control.py`, `participant.py`, `operator_api.py` y `__main__.py`.
- `backend/scripts/corrida_en_frio.py`.
- `backend/tests/loadtest/test_control.py`, `test_operator_api.py` y `test_participant.py`.
- `docs/pruebas/experimento-arena-en-vivo.md` y `docs/pruebas/README.md`.

## Cómo se verificó

- **Suite del backend:** 1257 aprobadas y 24 omitidas; ruff y mypy estricto limpios.
- **Prueba del límite por sesión en el gateway:** falla con el código anterior y pasa con el arreglo.
- **Corrida en frío LIVE con `claude-haiku-5-5`:** 15 pasos con emojis, varias líneas, doble envío, reintento idempotente, mensajes inválidos, memoria de conversación, memoria entre conversaciones y recarga del historial.
- **Control con 6 honestos y 20 atacantes simultáneos:**
  - Antes del arreglo: 23 de 54 intentos honestos al honeypot por `rate_limited`.
  - Después: 73 intentos en v0 → v1 → v2, con 0 desvíos, 0 bloqueos y 0 errores. Latencia p50 de 3.6 s y p95 de 14.5 s.
- **Gasto LIVE de la sesión de pruebas:** US$0.0958, con un tope de US$0.30.
- **Segunda corrida en frío tras los arreglos:** el carácter invisible devuelve `422`; las violaciones de los pasos 6 y 13 se reproducen.

## Riesgos y efectos en otros frentes

- **Llamadas sin contexto de arena:** el límite por agente no cambia. Un agente desbocado fuera de la arena sigue frenado.
- **Gasto con muchas sesiones:** el gasto total queda acotado por el tope diario de LLM y por el límite de intentos por sesión, no por el gateway.

## Pendiente

- Decidir los cuatro hallazgos de diseño del documento del experimento:
  - el punto se cuenta por acceso al dato;
  - `A-1001` como ejemplo en `get_order`;
  - identificadores internos en la respuesta;
  - el campo de texto se desactiva mientras se espera la respuesta.
- La corrida en frío [SUPUESTO: representa a un participante real] usa mensajes escritos por el equipo; la medición real será la del evento.
