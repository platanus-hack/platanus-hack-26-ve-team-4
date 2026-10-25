---
fecha: 2026-10-25
autor: "@CarSanoja"
rama: main
pr: ninguno  # push directo a main
estado: integrado
dominios: [frontend]
requisitos: []
---

# Monitor: cómo aprendió la defensa

## Qué cambió

- **Sección nueva.** El Monitor trae «Cómo aprendió la defensa» y reemplaza la lista «Versiones de política», que solo mostraba el código de la regla.
- **Qué es una política.** Arriba, una explicación en una frase: la lista de reglas que el gateway revisa antes de cada acción del agente, sin cambiar ni reentrenar el modelo. Debajo, los cuatro pasos del ciclo: ataque, regla, prueba y activación.
- **Una tarjeta por versión.** v0 es el punto de partida, sin reglas. Cada versión nueva cuenta:
  - qué faltaba;
  - la conversación que lo reveló;
  - qué regla se creó, en lenguaje claro y con su código;
  - cómo se probó (repeticiones del ataque bloqueadas y casos legítimos que siguen funcionando);
  - el efecto antes y después;
  - cuántos segundos pasaron desde el ataque hasta la activación.
- **Reglas heredadas.** Las de la versión padre se cuentan aparte, para que cada tarjeta muestre solo lo nuevo.
- **Explicación del analizador.** Queda plegada y rotulada como asesoría.

## Por qué

El Monitor mostraba `v1 · order_belongs_to_session_customer` sin decir qué es una política, qué no existía antes ni qué se creó. La narrativa del pitch (no había regla, un ataque la reveló, la defensa la escribió, la probó y la activó) necesita leerse en pantalla sin explicación oral.

## Archivos

- `frontend/src/features/monitor/`:
  - código: `policyChapters.ts` (datos), `PolicyStory.tsx` (vista), `policy-story.css`, más sus dos pruebas;
  - cambios: `MonitorPage.tsx` y `MonitorTrends.tsx` (sale la línea de tiempo), `monitor.css` (estilos de la línea de tiempo eliminados).
- `frontend/src/features/operator/api.ts`: el tipo `Policy` declara `evidence_attempt_ids`, `seconds` y `replay`, que el servidor ya enviaba.
- `docs/dominio/frontend.md`.

## Cómo se verificó

- Biome sin hallazgos (166 archivos), `tsc -b` sin errores, Vitest con 49 archivos y 235 pruebas en verde, y `pnpm build` correcto.
- En Chrome, en `http://127.0.0.1:8095/monitor` con la ronda local en `live`: la tarjeta v1 muestra «aprendida 14 s después del ataque», la conversación de N0-2, la regla «Solo se consultan los pedidos del cliente que está escribiendo», «Bloqueó 3/3 repeticiones del ataque y 5/5 casos de clientes legítimos siguieron funcionando» y «Pedido ajeno leído: antes ocurría → ahora bloqueado».

## Riesgos y efectos en otros frentes

- Los textos de las reglas cubren los cuatro validadores del catálogo. Una regla de flujo se describe de forma genérica y un código desconocido se muestra tal cual, sin inventar significado.
- El rótulo dice «conversación», no «ataque», porque el hueco puede destaparlo un cliente legítimo, como pasó con N0-2.

## Pendiente

- Nada.
