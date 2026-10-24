# Analyzer: hallazgos y explicación de evidencia

Estado: consolidación determinista y enriquecimiento LLM implementados. Este dominio recibe el `Assessment` de [oracles](./oracles.md), agrupa violaciones y ofrece explicaciones al operador. La evidencia que decide el resultado ya existe antes de consultar al modelo.

## Archivos y datos

| Archivo | Responsabilidad |
| --- | --- |
| [finding_service.py](../../backend/src/agent_zero/analyzer/finding_service.py) | Consolidar, listar, mitigar y reabrir hallazgos. |
| [models.py](../../backend/src/agent_zero/analyzer/models.py) | `FindingRecord` en `findings`; explicación por intento en `finding_explanations`. |
| [schemas.py](../../backend/src/agent_zero/analyzer/schemas.py) | `FindingAnalysis`, DTO cerrado para el rol `ANALYZER`. |
| [enrichment.py](../../backend/src/agent_zero/analyzer/enrichment.py) | Encolar `finding_analysis` y ejecutar el análisis como run durable. |
| [manifest.py](../../backend/src/agent_zero/analyzer/manifest.py) | Manifiesto 2.0.0 `analizador`, sin herramientas de negocio. |
| [operator_router.py](../../backend/src/agent_zero/arena/operator_router.py) | `GET /api/operator/findings`, con secreto de operación. |

`FindingRecord` conserva objetivo, herramienta, control ausente, primera versión afectada, intentos, IDs de evidencia, causa determinista, fechas y estado. No existe un endpoint público para crear o cerrar hallazgos; el panel los consulta y el ciclo de defensa actualiza sus estados.

## Consolidación determinista

`FindingService.record()` procesa exclusivamente los veredictos con `violated=true`. Calcula el fingerprint:

```text
objective_id : herramienta del objetivo : controles requeridos unidos con +
```

Por ejemplo, el objetivo de reembolso se vincula a `request_refund` y a los controles de titularidad e importe. La tabla objetivo → controles y las causas están en [validator_catalog.py](../../backend/src/agent_zero/policies/validator_catalog.py), no en una respuesta semántica.

La escritura reserva SQLite antes de leer el fingerprint. Si no existe, crea un hallazgo y guarda `finding_opened` con su outbox en la misma transacción. Si existe, agrega el intento una sola vez y une los IDs de eventos. El texto distinto del ataque no infla el número de hallazgos.

| Estado | Disparador |
| --- | --- |
| `open` | Primera violación con ese fingerprint. |
| `mitigated` | Defensa validada y activada que cubre el hallazgo. |
| `reopened` | Otra violación vinculada a un hallazgo mitigado, o rollback que elimina controles necesarios. |

`affected_policy_version` corresponde a la creación del hallazgo; las nuevas reproducciones están en `attempt_ids` y en la evidencia de cada intento. No interpretarlo como una lista de todas las versiones vulnerables. El estado es común a la ronda; no hay aún una matriz de mitigación por versión.

## Explicación del modelo

Después de confirmar la transacción, el servicio encola un run con clave `analysis:<finding_id>:<attempt_id>`. El handler comprueba que el intento esté vinculado al hallazgo, reúne su evaluación, mensajes y hasta 100 eventos, y declara el prompt `finding-analysis-v1`.

`FindingAnalysis` permite únicamente:

| Campo | Restricción |
| --- | --- |
| `attack_family` | Una familia de `AttackFamily`. |
| `probable_cause` | Texto de 1–1500 caracteres. |
| `reproduction_steps` | De 1 a 6 pasos de hasta 500 caracteres. |
| `limitations` | Texto de 1–1000 caracteres. |

El DTO es inmutable y rechaza campos extra. La llamada no tiene reparación automática (`repair_budget=0`). Mensajes, documentos y trazas se presentan como datos no confiables; el manifiesto del analizador no contiene herramientas de la tienda.

La explicación se guarda en una tabla separada, con clave compuesta `(finding_id, attempt_id)`, `status=available|unavailable`, error y fecha. Una salida inválida o un fallo del proveedor deja `unavailable`; el hallazgo y el veredicto siguen conservados. Un registro ya existente hace idempotente el handler. Si el proceso cae después de llamar al proveedor pero antes de guardar, el run puede repetir esa llamada: idempotencia de persistencia no significa facturación exactamente una vez.

La explicación no modifica el fingerprint, la causa de `FindingRecord`, su estado, las reglas ni el `Assessment`. Una clasificación errónea puede requerir revisión editorial sin cambiar una violación demostrada por estado.

## Vista HTTP

`GET /api/operator/findings` devuelve los datos consolidados y `analysis`:

- `null` mientras no hay explicación guardada;
- `status`, `advisory=true`, `attempt_id`, `error` y los campos tipados si está disponible;
- `status=unavailable`, error y ninguna explicación inventada si falló.

La consulta elige la explicación guardada más reciente de cada hallazgo. El campo principal `probable_cause` de la vista sigue siendo el valor determinista; la explicación semántica vive dentro de `analysis`. La arena pública recibe sólo agregados y eventos permitidos de [events](./events.md).

## Pruebas hechas y repetición

Desde la raíz:

```bash
cd backend
uv run pytest tests/evals/test_analyzer.py tests/arena/test_core_cycle.py tests/arena/test_multiturn.py tests/arena/test_control_concurrency.py -q
```

| Archivo | Escenario comprobado |
| --- | --- |
| [test_analyzer.py](../../backend/tests/evals/test_analyzer.py) | Explicación DEMO disponible, enlazada al intento; causa y estado deterministas intactos. |
| Mismo archivo | Un DTO malicioso que intenta añadir `violation_status` o `status` se rechaza y deja `unavailable`. |
| [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py) | Hallazgo, candidato, validación, activación y repetición sobre la política nueva. |
| [test_multiturn.py](../../backend/tests/arena/test_multiturn.py) | Un intento con varios objetivos produce controles conjuntos y evidencia de cada violación. |
| [test_control_concurrency.py](../../backend/tests/arena/test_control_concurrency.py) | Rollback y activación serializados con admisión; reconciliación del estado. |

El ensayo LIVE registró tres llamadas del rol `ANALYZER`; su texto es asesoría de ese ensayo, no una medición independiente de precisión del clasificador. Los resultados de integración y hashes están en [evidencias](../pruebas/evidencias.md).

## Extensión y límites

Para añadir un objetivo, definir primero su oráculo, herramienta y controles en el catálogo; extender `OBJECTIVE_TOOLS`, tests y agrupación de manera conjunta. Antes de añadir clasificación multilabel, versionar el DTO y decidir cómo presentar discrepancias sin convertir una etiqueta semántica en permiso.

Quedan como mejoras la historia de mitigación por versión, revisión humana de explicaciones y estrategias explícitas de reintento editorial. No cambiar el fingerprint para incorporar la redacción del LLM: rompería la consolidación y haría depender la contabilidad de un proveedor variable. Para retomar el trabajo, ver [continuidad](../continuidad.md).
