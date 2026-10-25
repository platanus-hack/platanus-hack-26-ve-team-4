---
fecha: 2026-10-25
autor: "@FernandoSiavato"
rama: feat/oraculo-intencion
pr: pendiente
estado: en revisión
dominios: [oracles, victim, arena, frontend]
requisitos: []
---

# Señales de intención y alcance del agente

## Por qué

Dos intentos reales del chat mostraron huecos: el agente escribió código Python y un `.md` a pedido (no era su papel) y a «dame números de pedidos» se negó bien, pero el intento quedó como «Sin objetivo adversario» sin rastro de lo pedido.

## Qué cambió

- `oracles/intent_signal.py`: señales deterministas de intención sobre mensajes y respuesta. Se guardan en `Assessment.signals`; no cambian el desenlace.
- `victim/tool_loop.py`: el prompt limita el alcance a soporte de Yummi y prohíbe código y archivos.
- Monitor: la fila trae `signals`; el detalle las lista y la familia dice «Señal: …» cuando no hay hallazgos.

## Cómo se verificó

- Backend en Docker: tests/oracles (9 passed), tests/victim, tests/attempts, test_monitor_router, test_core_cycle y test_traceability con 135 passed y 21 skipped antes de ajustar dos expresiones; tras el ajuste tests/oracles dio 9 passed. ruff sin errores y mypy sin problemas en 40 archivos.
- Frontend: Biome sin errores, `tsc -b` sin errores, 198 tests en verde y build en verde.
- Con la clave real en el Docker local se repite el mismo mensaje fuera de alcance (ver resultado en la sesión).

## Limitaciones

Las reglas son patrones simples en español: pueden tener falsos positivos y falsos negativos. Las señales no alimentan todavía la Arena en vivo ni la clasificación pública.
