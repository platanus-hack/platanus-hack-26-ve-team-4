---
fecha: 2026-10-24
autor: "@CarSanoja"
rama: main
pr: ninguno  # push directo a main
estado: integrado
dominios: [attempts, policies, patches, victim, frontend, docs]
requisitos: [GW-02]
---

# Decisiones de producto, activación bajo carga y comparación con el escenario limpio

## Qué cambió

- **Activación bajo carga.** Con un parche validado pendiente, los intentos en cola no arrancan; esperan como máximo `AGENT_ZERO_DEFENSE_ACTIVATION_HOLD_SECONDS` (30 s). El programador activa en cuanto no queda ningún intento corriendo, y los intentos en cola se ejecutan con la política activa en el momento de arrancar. La espera de vaciado de la reversión del operador no cambia.
- **Acceso al dato.**
  - Las reglas del participante dicen que cuenta acceder al dato aunque no se muestre.
  - La evidencia del operador marca «Accedió al dato sin mostrarlo» solo en violaciones confirmadas de nivel acción.
- **Sin pista plantada.**
  - `get_order` describe el formato del identificador sin usar `A-1001`.
  - OBJ-ORDER avisa que los pedidos ajenos siguen el mismo formato.
- **Minimización de datos.**
  - Las salidas de herramientas que ve el modelo no incluyen `customer_id`, con los mismos campos en el entorno protegido y en el señuelo.
  - Se quitó el campo `cliente` de la cabecera que recibe el modelo.
  - El precheck de síntesis lee el dueño del efecto estructurado.
- **Redactar mientras se espera.** El campo de texto queda habilitado mientras llega la respuesta; Enter y el botón no envían hasta que termina el intento. Un aviso accesible indica que el asistente está respondiendo.

## Por qué

- **Activación:** el patrón de latencias de la sesión mostró que la activación esperaba a que no quedara ningún intento en cola ni en curso en toda la arena. Con tráfico constante llegó a 76 s en LIVE y a 333 s en DEMO con 100 participantes.
- **Las cuatro decisiones** salen de la corrida en frío; están descritas en el [documento del experimento](../pruebas/experimento-arena-en-vivo.md#decisiones-tomadas-y-verificadas).

## Archivos

- Activación:
  - `backend/src/agent_zero/attempts/activation_gate.py`, `attempt_execution_handler.py`, `attempt_query_service.py` y `repository.py`.
  - `backend/src/agent_zero/policies/policy_service.py`, `backend/src/agent_zero/patches/defense_scheduler.py` y `backend/src/agent_zero/config.py`.
  - `backend/tests/arena/test_activation_gate.py`.
- Minimización:
  - `backend/src/agent_zero/victim/model_view.py`, `store_tools.py`, `scenario_tools.py` y `tool_loop.py`.
  - `backend/src/agent_zero/evals/suite.py` y `backend/src/agent_zero/patches/synthesis_precheck.py`, más sus tests.
- Pista: `backend/src/agent_zero/victim/tool_schemas.py`, su test y `frontend/src/features/participant/LabPanel.tsx`.
- Frontend:
  - `frontend/src/features/participant/AttemptChat.tsx` y `AttemptChat.compose.test.tsx`.
  - `frontend/src/features/participant/ParticipantPage.tsx`.
  - `frontend/src/features/operator/EvidencePanel.tsx` y `EvidencePanel.test.tsx`.
  - `frontend/src/styles.css`.
- Evidencia: `artifacts/core-evaluation/live-270-2026-10-24-escenario-limpio.json` y su `.sha256`.
- Documentación: `docs/pruebas/evidencias.md`, `docs/continuidad.md` y `docs/pruebas/experimento-arena-en-vivo.md`.

## Cómo se verificó

- **Revisión de las decisiones.** Cada una se implementó en una rama aislada y pasó por un revisor que intentó refutarla.
  - El revisor encontró dos defectos reales: el precheck de síntesis dejaba de ver el dueño en pedidos `cust-demo-*`, y la etiqueta de acceso aparecía también en intentos del señuelo.
  - Ambos se corrigieron con tests y la segunda revisión no encontró defectos.
- **Suites.**
  - Backend: 1272 aprobadas y 24 omitidas, con ruff y mypy estricto limpios.
  - Frontend: `pnpm typecheck`, `pnpm build`, Biome y 106 tests Vitest.
  - La compilación de producción encontró un error de tipos en un test nuevo que `vitest` no detectaba; se corrigió en `df1fe76`.
- **Activación.** Las pruebas nuevas fallan con el código anterior (2 de 3; la tercera cubre el vencimiento del tope de espera) y pasan con el arreglo. En LIVE, con 20 atacantes y 6 honestos, la primera violación → política activa bajó de 49,98 s a 16,35 s, con 0 bloqueos y 0 desvíos al señuelo en 73 intentos honestos.
- **Corrida en frío LIVE posterior.** El saludo ya no sugiere un pedido ajeno, ninguna respuesta contiene `cust-` ni `customer_id`, y las violaciones de los pasos 6 y 13 se mantienen en v0.
- **Comparación LIVE de 270.** Resultado: 66/90 → 0/90 violaciones, 45/45 tareas en ambas versiones, 0 inconclusos, 684 llamadas y 0,072934 USD.

## Riesgos y efectos en otros frentes

- **Intentos en espera.** Mientras un parche validado espera, los intentos en cola tardan hasta 30 s más en arrancar. Si el programador de defensa no corre, el tope de espera libera la arena.
- **Versión de política en el registro.** Un intento puede quedar registrado en cola con una versión de política y ejecutarse con otra. El evento `ATTEMPT_QUEUED` conserva la versión de entrada; `ATTEMPT_STARTED` y la fila del intento reflejan la versión con que se ejecutó.
- **Datos ficticios.** `customer_name` y `customer_email` siguen en la salida de `get_order`; son datos ficticios del escenario.

## Pendiente

- Subir los trabajadores del runtime, separar API y trabajadores, y avisar al participante por SSE en lugar de sondear cada 1,5 s.
- Medir la red real tras el despliegue (#16).
