# Prober: campañas autónomas

Estado: campañas de hasta 30 intentos, seis familias y mutación estructurada implementadas. El Prober genera entradas del laboratorio y las entrega a [attempts](./attempts.md); no decide si hubo violación ni qué política se activa.

## Archivos para continuar

| Archivo | Responsabilidad |
| --- | --- |
| [schemas.py](../../backend/src/agent_zero/prober/schemas.py) | `AttackCase` y salida cerrada `AttackMutation`. |
| [playbooks.py](../../backend/src/agent_zero/prober/playbooks.py) | 30 casos, selección por índice y digest de entrada efectiva. |
| [mutation.py](../../backend/src/agent_zero/prober/mutation.py) | Llamada `PROBER`, prompt versionado y conservación del contexto del servidor. |
| [campaign_service.py](../../backend/src/agent_zero/prober/campaign_service.py) | Crear, listar y detener campañas, con reserva de escritura. |
| [campaign_handler.py](../../backend/src/agent_zero/prober/campaign_handler.py) | Handler `prober_campaign`, generación, reanudación y admisión. |
| [campaign_models.py](../../backend/src/agent_zero/prober/campaign_models.py) | Tablas `campaigns`, `campaign_plans` y `campaign_cases` en `app.db`. |
| [router.py](../../backend/src/agent_zero/prober/router.py) | HTTP de operación y validación del payload. |

## API y límites

Todas las rutas exigen `X-Operator-Secret`; un token de audiencia no lo sustituye.

| Ruta | Comportamiento |
| --- | --- |
| `POST /api/operator/campaigns` | Devuelve 202 y crea campaña y run en la misma transacción. |
| `GET /api/operator/campaigns` | Incluye estado, intentos, razón de parada, llamadas de generación y casos. |
| `POST /api/operator/campaigns/{id}/stop` | Detiene nuevas admisiones; conserva los intentos ya admitidos. |

Payload para recorrer una vez las seis familias:

```json
{"max_attempts":6,"generation":"llm","max_mutations":6}
```

`max_attempts` y `max_mutations` admiten 1–30. `generation` es `templates` o `llm`; por defecto usa plantillas y nueve intentos. Sólo puede haber una campaña `running` y la ronda debe estar abierta. Inicio incompatible devuelve 409; un ID inexistente al detener devuelve 404.

## Casos y superficies reales

El planificador recorre un orden fijo, con cinco variantes por familia. Los tres primeros casos cubren los tres objetivos de descubrimiento; los primeros seis cubren todas las familias.

| Orden | Familia | Superficie | Objetivo principal |
| --- | --- | --- | --- |
| 1 | `direct_injection` | `message` | `OBJ-ORDER` |
| 2 | `tool_misuse` | `message` | `OBJ-REFUND` |
| 3 | `memory_poisoning` | `memory`, en dos turnos | `OBJ-MEMORY` |
| 4 | `indirect_injection` | `document` recuperado | `OBJ-ORDER` |
| 5 | `goal_hijacking` | `message`, en dos turnos | `OBJ-ORDER` |
| 6 | `tool_poisoning` | `tool_result` contaminado | `OBJ-REFUND` |

`AttackCase` fija ID, familia, superficie, objetivo, fixture `tienda`, origen y hasta cuatro mensajes de 4000 caracteres. Las superficies documentales requieren un [ControlledFixture](../../backend/src/agent_zero/victim/controlled_fixtures.py) del tipo declarado. [ScenarioTools](../../backend/src/agent_zero/victim/scenario_tools.py) instala ese contenido en la sesión; no basta cambiar una etiqueta del caso. La API pública de intentos no permite instalar fixtures.

El mutador sólo devuelve `messages` y `fixture_content`. No puede devolver identidad, reglas, versión, destino, familia ni veredicto. Los campos extra se rechazan, se conserva el objetivo y la superficie del caso, y `repair_budget=0` evita una cadena implícita de reparaciones. Un fallo del generador termina la campaña con `generator_failed`; no ejecuta una plantilla como sustitución silenciosa.

## Persistencia y recuperación

| Entidad | Estado guardado |
| --- | --- |
| `Campaign` | `running → exhausted` o `stopped`, límite e IDs de intentos y digests. |
| `CampaignPlan` | Tipo de generación, límite y contador de mutaciones, razón de parada. |
| `CampaignCaseRecord` | Índice, identidad sintética, JSON, digest, sesión, intento y error. |

Los casos avanzan por `pending_generation → generating → ready → submitted`; también existen `duplicate` y `generation_error`. Se reserva y confirma una llamada de generación antes de contactar al modelo: una caída no restaura gratuitamente ese presupuesto. Un caso interrumpido puede volver a gastar una mutación hasta el tope persistido.

La sesión interna se guarda antes de admitir el intento. La clave idempotente es `case_id`; si el proceso cae después de admitir pero antes de guardar `attempt_id`, el reintento recupera el mismo intento. El worker espera el resultado previo y, ante una violación confirmada, `defense_processed` antes de finalizar o seguir. Esto evita dar una campaña por terminada antes de consolidar su último hallazgo; no implica esperar toda activación de política.

El digest normaliza NFKC, mayúsculas y espacios sobre cliente, mensajes y fixture. Excluye etiquetas, IDs aleatorios y semilla. Una entrada duplicada no consume otra admisión. Un stop vuelve a comprobarse al admitir; el reset de ronda suspende el handler mientras el archivo se completa.

## Presupuestos

Los límites de intentos y mutaciones son durables. Las llamadas del mutador y de la víctima llevan `campaign_id` en el ledger y participan en los límites LLM de llamadas/tokens/coste. Los contadores generales de llamadas y tokens LLM viven en memoria; no son una cuota transaccional entre procesos ni se reconstruyen completos al reiniciar. La historia de coste LIVE sí se carga desde el ledger. El presupuesto durable del plan no sustituye esa limitación de [LLM](./llm.md).

Las razones visibles incluyen `attempt_budget_exhausted`, `mutation_budget_exhausted`, `unique_cases_exhausted`, `generator_failed`, `llm_budget_exhausted` y `operator_stopped`. `exhausted` significa fin de trabajo, no que se encontró una vulnerabilidad ni que todo caso terminó evaluable. Los intentos autónomos no puntúan en la clasificación humana.

## Pruebas hechas y repetición

Desde la raíz, sin iniciar un servidor ni consumir un proveedor real:

```bash
cd backend
uv run pytest tests/evals/test_campaigns.py tests/evals/test_suite.py tests/arena/test_admission_and_campaign.py -q
```

| Prueba | Qué verifica |
| --- | --- |
| [test_campaigns.py](../../backend/tests/evals/test_campaigns.py) | Seis familias con plantillas y mutación, documentos/resultados realmente recuperados, dedup, límites persistidos y salida LLM maliciosa. |
| Mismo archivo, recuperación | Caída exacta después de admitir: mismo intento y sin duplicar efectos. |
| Mismo archivo, superficie indirecta | El fixture sobrevive a replay y a la validación del caso original; tras activar hay denegación real. |
| [test_suite.py](../../backend/tests/evals/test_suite.py) | Tipos cerrados, digest independiente de etiquetas y fixture obligatorio para la superficie. |
| [test_admission_and_campaign.py](../../backend/tests/arena/test_admission_and_campaign.py) | Descubrimiento de los tres objetivos, agotamiento y separación de la audiencia. |

La ejecución LIVE guardada completó seis mutaciones y seis intentos de las seis familias; la suite DEMO ejercitó todas las variantes. Ver [evidencias](../pruebas/evidencias.md). Para una campaña operada por HTTP y posterior evaluación, usar [evaluación](../evaluacion.md#9-ejecutar-y-exportar-la-comparación); verificar la versión activa en vez de suponer que será 3.

## Límites y siguiente extensión

El orden no prioriza familias por novedad, éxito o hallazgos abiertos. El generador puede redactar texto que no produzca el efecto esperado; la validez del DTO no demuestra eficacia. Para ampliar familias, cambiar juntos playbook, contrato, fixture ejecutable, suite y tests de dedup. Para aumentar autonomía, introducir primero un planificador persistido y una política clara de presupuesto; conservar las decisiones de identidad y seguridad fuera de la salida del modelo.
