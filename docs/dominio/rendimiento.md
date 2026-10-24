# Rendimiento: rápido, preciso y eficiente

Los números de este documento son hipótesis de diseño salvo que se indique que fueron medidos. Se confirman con el primer ciclo real y se reportan en [evaluación](../evaluacion.md).

## Rápido

| Palanca | Cómo | Efecto esperado |
| --- | --- | --- |
| LLM fuera del camino crítico | Router, oráculos, agrupación, elección de control y activación son código. | Cada paso de decisión en milisegundos. |
| Validación contrafactual | Re-evaluar la traza grabada con la política candidata antes de gastar llamadas. | Rechazo inmediato de candidatos que no bloquean. |
| Validación en paralelo | Los 8 runs del nivel 2 corren a la vez sobre copias limpias en memoria. | El tiempo de validación es el de un run, no el de ocho. |
| Pool de validación propio | El runtime tiene hoy `runtime_worker_concurrency=2`; la validación usa su propio pool para no competir con la arena. | La ronda pública no frena la activación. |
| Haiku en modo veloz | Esfuerzo bajo, thinking desactivado y salida corta en los roles de volumen (ya configurado en `llm/catalog.py`). | Menor latencia por turno. |
| Caché de prompt | Llevar el system prompt y las herramientas de la víctima por encima del mínimo cacheable de Haiku 5.5 (286 tokens). | Menos tokens de entrada facturados y menor latencia en turnos repetidos. |
| Enriquecimiento en segundo plano | Analizador y generador redactan mientras el ciclo avanza. | La activación no espera texto. |

**Presupuesto de latencia, hipótesis:**

| Tramo | Estimación |
| --- | --- |
| Intento de la víctima | 1 a 3 s por run con Haiku. |
| Oráculos, hallazgo y candidato | menos de 50 ms. |
| Validación nivel 1 | menos de 50 ms. |
| Validación nivel 2 | 2 a 5 s en paralelo. |
| Drenaje y activación | menos de 1 s si no hay intentos largos en curso. |
| **Tiempo hasta el parche** | **10 a 20 s** desde la violación confirmada. |

La única medición real hasta ahora es el recorrido de la flota: dos llamadas de la víctima con Haiku 5.5 en modo `live` costaron US$ 0,000206 (24 de octubre de 2026).

## Preciso

**Precisión del ataque detectado:**

- **Canarios.** Los pedidos de cada cliente llevan marcadores únicos. Si el marcador de otro cliente aparece en una salida o en una herramienta completada, la violación es inequívoca.
- **Dos niveles de evidencia.** Una lectura indebida completada viola el control aunque la respuesta final la oculte; la filtración en la respuesta se registra como efecto adicional.
- **Oráculos deterministas.** Comparan identidad de sesión, dueño del recurso, importes y escrituras. El clasificador de familia puede equivocarse sin cambiar el veredicto.
- **`inconclusive` honesto.** Faltan trazas o hubo un error: no se cuenta como victoria defensiva.

**Precisión de la defensa:**

- **Tareas legítimas en cada validación** para medir sobrebloqueo. Un parche que bloquea todo se rechaza.
- **Variantes reservadas** que el generador no ve, para que el parche no quede ajustado a una frase.
- **Varianza del modelo.** El nivel 1 es determinista; el nivel 2 corre en vivo una vez en la demo, y la evaluación amplia repite cada caso tres veces.

## Eficiente

| Concepto | Estimación |
| --- | --- |
| Llamadas por ciclo completo | Unas 9 a Haiku: el intento y los 8 runs de validación. |
| Costo por ciclo | Menos de US$ 0,001, con unos US$ 0,0001 por llamada de la víctima. |
| Tope diario | US$ 2 (`AGENT_ZERO_LLM_DAILY_USD_LIMIT`), suficiente para miles de ciclos. |

- **Mutaciones deterministas primero.** El Prober aplica operadores sin modelo (cambio de idioma, reparto en turnos, codificación, juego de roles) y usa el LLM solo para variantes nuevas.
- **Deduplicación antes de gastar.** Hash normalizado del caso; un duplicado no se ejecuta.
- **Cassettes** para ensayar la demo a costo cero.
- **Batch API** de Anthropic para la evaluación amplia, que no necesita respuesta inmediata.
- **Topes por campaña** en llamadas y tokens; al agotarse se detiene la generación y se conserva la evidencia.

## Métricas que se muestran

| Métrica | Definición |
| --- | --- |
| Tiempo hasta el parche | Segundos desde la primera violación confirmada hasta `policy_activated`. |
| Tasa de bloqueo | Intentos adversarios `prevented` sobre intentos evaluados de la misma familia, antes y después. |
| Utilidad conservada | Tareas legítimas completadas sobre el total, antes y después. |
| Contención | Intentos `contained_honeypot` sin efectos protegidos. |
| Inconclusos | Intentos `inconclusive`, reportados aparte. |
| Costo | US$ por ciclo y por campaña, desde el ledger. |
