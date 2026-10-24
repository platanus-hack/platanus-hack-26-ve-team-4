# Rendimiento y capacidad: datos y límites

Este documento separa mediciones del laboratorio, configuración y objetivos pendientes. La fuente de resultados es la [evidencia exportada](../pruebas/evidencias.md), no una estimación de rendimiento de producción.

## Lo medido

| Ensayo guardado | Resultado | Qué permite concluir |
| --- | --- | --- |
| Comparación DEMO | 270 ejecuciones, 732 llamadas simuladas, cero inconclusos. | Consistencia del flujo y de los controles en los casos publicados. |
| Utilidad DEMO | 45/45 tareas correctas por versión. | La suite legítima publicada se conserva; no cubre cualquier tarea de soporte. |
| Comparación LIVE | 270 ejecuciones, 683 llamadas de evaluación `live`, cero inconclusos. | Con `claude-haiku-5-5`, las violaciones pasan de 59/90 a 0/90; la latencia por llamada tiene mediana de 1,15 s. |
| Coste de la comparación LIVE | US$0.064237 medidos en evaluación, US$0.075079 con la campaña. | Coste de esa corrida, 0,0000941 por llamada de evaluación; no una factura ni coste por usuario. |
| Ciclo LIVE | 93 llamadas de los cinco roles, once comprobaciones aprobadas. | El circuito funciona con el proveedor real configurado. |
| Coste LIVE | US$0.0101596 estimados desde tokens y tarifas del ledger. | Coste estimado de ese ensayo concreto; no una factura ni presupuesto por usuario. |
| Ensayo inicial LIVE | Timeout de 60 segundos del verificador de campaña, preservado con error. | Un límite global corto no cubría seis casos más sus validaciones; el comando final espera por caso. |

El informe DEMO contiene medianas y p95 por versión, con tamaño de muestra. Esas latencias pertenecen al intérprete determinista y al almacenamiento local. No extrapolarlas a una conversación LIVE, una red móvil o un despliegue con carga.

## Configuración actual

Valores base de [Settings](../../backend/src/agent_zero/config.py), salvo que se indique el ejemplo:

| Control | Valor y alcance |
| --- | --- |
| Worker de runs | Concurrencia 2, polling 0,5 segundos; configurable. |
| Validación de candidato | Semáforo de hasta 8 casos; comparten un run de validación. |
| Participantes | 100 identidades por ronda, máximo configurable 500. Sesiones vencidas conservan plaza hasta reset. |
| Cola de intentos | Límite 40, límite por sesión 1 y 12 envíos por minuto; ver separación de orígenes en `attempts`. |
| Herramientas | 60 llamadas por minuto por agente en el limiter del proceso. |
| LLM del ejemplo | 5000 llamadas por día y 1200 por campaña en `.env.example`; los valores base de Settings son 2000 y 300. |
| Tokens y dinero | Ejemplo: 1.500.000 tokens por campaña y US$2 diarios estimados. No es un límite duro de facturación del proveedor. |

Tener 100 identidades no demuestra que el sistema sostenga 100 llamadas simultáneas. Las pruebas de asignación concurrente y varios workers verifican integridad, no capacidad ni tiempos bajo carga real.

## Costes que deben tenerse en cuenta

Una conversación puede requerir varios turnos de modelo: propuesta, resultado de herramientas y respuesta final. Ocho casos de validación no equivalen a ocho llamadas. La suite amplia de tres repeticiones exige al menos 672 llamadas por sus turnos y puede consumir más; el ensayo publicado utilizó 732.

`AnalyzerHandler` puede ejecutarse en paralelo al ciclo. La explicación de `PatchExplainer` se espera dentro del run de validación y añade latencia. El cliente del modelo agrupa un stream completo antes de entregarlo al loop cuando usa reintentos; la UI recibe estado por polling/SSE, no tokens incrementales del proveedor.

SQLite serializa escrituras; auditoría y ledger releen sus registros para ciertas operaciones. Los límites generales LLM y de herramientas son locales al proceso. Añadir réplicas sin rediseñar cuotas, almacenamiento y operación no multiplica la capacidad de forma garantizada.

## Próxima medición reproducible

1. Fijar commit, hardware/despliegue, modo/proveedor, modelo y configuración; usar datos de ensayo nuevos.
2. Separar consultas propias, ataques, validación y tráfico de observación SSE.
3. Medir llegadas, concurrencia real, profundidad de cola, errores, inconclusos y consumo del proveedor.
4. Registrar latencia de intento, duración de validación y tiempo desde hallazgo hasta activación, con `n`, mediana y p95.
5. Repetir con la misma carga y las dos versiones; conservar ejecuciones fallidas y pendientes.

La meta de diez sesiones conectadas y un parche en 30 segundos sigue pendiente de medición bajo carga real. No publicar esa meta como un SLA. Antes de optimizar, revisar las garantías de [runtime](./runtime.md), [gateway](./agent-gateway.md) y [telemetry](./telemetry.md), y conservar la [regresión de concurrencia](../pruebas/por-dominio.md#runtime-eventos-y-auditoría).
