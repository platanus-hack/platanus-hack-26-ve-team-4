# Matriz de pruebas por dominio

Usar esta matriz para elegir la regresión de un cambio. El comando base es `cd backend && uv run pytest <rutas> -q`; los nombres de archivo son enlaces a las pruebas reales. Configuración y resultados globales en [la guía de pruebas](./README.md).

## Colección de referencia

La colección documental comprobada sobre el código vigente recoge 862 casos. Los números incluyen parametrizaciones y no equivalen a requisitos independientes ni a porcentajes de cobertura de líneas.

| Carpeta bajo `backend/tests/` | Casos recogidos | Dominio o integración |
| --- | ---: | --- |
| `agent_gateway` | 63 | Permisos, etapas, herramientas y auditoría. |
| `arena` | 35 | Ciclo del producto, oráculos, routing, patches, recuperación y rondas. |
| `armor` | 372 | Corpus de ataques, texto legítimo, normalización y PII. |
| `evals` | 22 | Prober, analizador, suite amplia y recuperación. |
| `decoy` | 24 | Cebos, honeytoken, traza y métricas del señuelo, tarjeta de revelación. |
| `events` | 6 | Broker y SSE; outbox adicional en `arena`. |
| `fleet` | 40 | Composición, admisión, principal, arranque e integración. |
| `identity` | 27 | Firma, scopes, expiración y revocación. |
| `llm` | 79 | Instrumentación, cuotas, cassettes y dos tests LIVE opcionales. |
| `memory_bank` | 24 | Cifrado, aislamiento, retención y borrado. |
| `policies` | 10 | Esquema y transiciones; activación integrada en `arena`. |
| `registry` | 65 | Manifiestos, descubrimiento, integridad y HTTP. |
| `runtime` | 51 | Runs, reintentos, cancelación, leases y trazas. |
| `sessions` | 3 | Creación y proyección; concurrencia adicional en `arena`. |
| `shared` | 3 | Salud y clasificación. |
| `telemetry` | 31 | Spans, auditoría, ancla y journal. |
| `victim` | 23 | Herramientas de flota, respuestas y parsing de turnos. |
| `walkthrough` | 4 | Cliente y recorrido de flota. |
| Raíz | 4 | Arranque de app y trazabilidad documental. |

## Producto: sesiones, intentos y escenarios

```bash
cd backend
uv run pytest tests/sessions tests/arena tests/victim tests/policies -q
```

| Si cambias… | Pruebas que deben revisarse | Qué protegen |
| --- | --- | --- |
| Sesiones, token o cupo | [test_router.py](../../backend/tests/sessions/test_router.py), [test_round_reset.py](../../backend/tests/arena/test_round_reset.py), [test_admission_and_campaign.py](../../backend/tests/arena/test_admission_and_campaign.py) | Consentimiento, visibilidad, identidad única, sesión vencida/reset y cupos. |
| Admisión, idempotencia, versión o ruta | [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py), [test_control_concurrency.py](../../backend/tests/arena/test_control_concurrency.py), [test_recovery.py](../../backend/tests/arena/test_recovery.py) | Payload repetido frente a cambiado, admisión concurrente con activación/reversión y recuperación. |
| Herramientas o transacción de negocio | [test_environment_transactions.py](../../backend/tests/arena/test_environment_transactions.py), [test_tool_retries.py](../../backend/tests/arena/test_tool_retries.py) | Saldo compartido entre pools y efectos únicos tras reintento. |
| Formato de la traza de herramientas | [test_tool_trace_contract.py](../../backend/tests/arena/test_tool_trace_contract.py), [test_trace_reader.py](../../backend/tests/victim/test_trace_reader.py) | Esquema v2, salida y efecto por herramienta, denegación con validador, `tool_failed`, «lo hice» sin efecto, lectura v1 y falla cerrada. Contrato en [traza de herramientas](../dominio/traza-herramientas.md). |
| Oráculos, límite de reembolso o memoria | [test_business_objectives.py](../../backend/tests/arena/test_business_objectives.py), [test_multiturn.py](../../backend/tests/arena/test_multiturn.py) | Lecturas indebidas, efectos aunque se filtre la salida, fraccionamiento y varios objetivos. |
| Política, validación o explicación | [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py), [test_patch_explanation.py](../../backend/tests/arena/test_patch_explanation.py), [test_lifecycle.py](../../backend/tests/policies/test_lifecycle.py) | Utilidad, rechazo por sobrebloqueo, actor generado y asesoría que no modifica reglas. |
| Stream nativo | [test_model_turn.py](../../backend/tests/victim/test_model_turn.py) | Fragmentos JSON, IDs duplicados, bloques incompletos, truncamiento y límites antes de ejecutar efectos. |

No hay una carpeta `tests/oracles` o `tests/patches`: las pruebas de sus efectos están integradas en `arena` y `evals`. Que un DTO pase su test no sustituye la comprobación de estado de negocio.

## Autonomía y comparación

```bash
cd backend
uv run pytest tests/evals -q
```

| Archivo | Escenarios |
| --- | --- |
| [test_campaigns.py](../../backend/tests/evals/test_campaigns.py) | Seis familias, fuentes controladas, generación estructurada, deduplicación, presupuesto durable y recuperación tras admisión. |
| [test_analyzer.py](../../backend/tests/evals/test_analyzer.py) | Explicación de fondo separada del veredicto y rechazo de campos que pretenden cambiarlo. |
| [test_full_evaluation.py](../../backend/tests/evals/test_full_evaluation.py) | Grid completo de 270 ejecuciones sobre herramientas reales del escenario con proveedor demo; utilidad, datos aislados y ledger. |
| [test_recovery.py](../../backend/tests/evals/test_recovery.py) | Reinicio con resultados ya guardados, suite/política alteradas, cancelación después de un reembolso y limpieza del entorno. |
| [test_suite.py](../../backend/tests/evals/test_suite.py) | Número de casos, familias, particiones, hashes y límites de los contratos. |
| [test_unavailable_provider.py](../../backend/tests/evals/test_unavailable_provider.py) | Errores e inconclusos con ejecuciones pendientes; no se convierten en victorias. |

Los tests de la evaluación ejecutan múltiples conversaciones por caso de pytest y tardan más que los esquemas. No necesitan clave LIVE. El [CLI de evaluación](../dominio/evals.md) es un ensayo distinto contra un servidor persistente.

## Runtime, eventos y auditoría

```bash
cd backend
uv run pytest tests/runtime tests/events tests/telemetry tests/arena/test_transactional_events.py tests/arena/test_round_reset.py -q
```

| Prueba clave | Fallo que reproduce |
| --- | --- |
| [test_run_leases.py](../../backend/tests/runtime/test_run_leases.py) | Dos workers sobre el mismo paso, propietario vencido y heartbeat de un paso lento. |
| [test_transactional_events.py](../../backend/tests/arena/test_transactional_events.py) | Rollback, caída tras commit, caída después de auditoría, dispatchers concurrentes y SSE que lee eventos remotos en orden sin notificación del broker local. |
| [test_sse.py](../../backend/tests/events/test_sse.py), [test_broker.py](../../backend/tests/events/test_broker.py) | Formato, cursor, eventos privados, historia y suscripción local. |
| [test_round_reset.py](../../backend/tests/arena/test_round_reset.py) | Archivo completo, token antiguo, cambio de ronda y recuperación tras reset interrumpido. |
| [test_audit_durability.py](../../backend/tests/telemetry/test_audit_durability.py) | Appends multiproceso, journal y caída durante publicación de la línea/ancla. |

Conservar estas pruebas si se sustituye SQLite o se extraen workers a otro servicio. Un lock local no reemplaza los guards persistentes que esas pruebas ejercitan.

## Plataforma de seguridad y LLM

```bash
cd backend
uv run pytest tests/registry tests/identity tests/memory_bank tests/agent_gateway tests/armor tests/fleet -q
uv run pytest tests/llm -q
```

Los documentos [registry](../dominio/registry.md), [identity](../dominio/identity.md), [memoria](../dominio/memory-bank.md), [gateway](../dominio/agent-gateway.md), [Armor](../dominio/armor.md) y [LLM](../dominio/llm.md) enlazan los casos específicos. La flota conecta las primitivas con credenciales verificadas; un test de servicio con un guard de prueba no equivale a una identidad autorizada por sí solo.

## Frontend

Desde la raíz:

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

| Pruebas | Cobertura |
| --- | --- |
| [ParticipantPage.test.tsx](../../frontend/src/features/participant/ParticipantPage.test.tsx), [storage.test.ts](../../frontend/src/features/participant/storage.test.ts) | Recuperación de sesión, datos inválidos y reconciliación de historial. |
| [AttemptChat.test.tsx](../../frontend/src/features/participant/AttemptChat.test.tsx) | De uno a cuatro turnos, respuesta perdida y reintento con la misma clave. |
| [useArenaEvents.test.ts](../../frontend/src/features/arena/hooks/useArenaEvents.test.ts), [ArenaPage.test.tsx](../../frontend/src/features/arena/ArenaPage.test.tsx) | Eventos malformados/privados, reconexión, modo y cambio de ronda. |
| [OperatorPage.test.tsx](../../frontend/src/features/operator/OperatorPage.test.tsx) | Autorización, exclusión de acciones, evaluación y reset. |
| [http.test.ts](../../frontend/src/shared/api/http.test.ts), [usePolling.test.ts](../../frontend/src/shared/api/usePolling.test.ts) | Errores HTTP, credenciales antiguas, cancelación y ausencia de polls superpuestos. |

Son 47 pruebas de componentes y hooks en jsdom. El build no comprueba diseño visual, interacción en un navegador real ni acceso móvil externo.

## Cambios que requieren más de una suite

Un cambio en un DTO público debe revisar router/backend, tipo espejo y componentes/frontend. Una herramienta nueva afecta manifiesto, identidad, gateway, víctima, política, oráculo y utilidad. Un cambio de estado durable afecta el worker, recuperación, outbox y snapshot de ronda. Un nuevo proveedor afecta cassettes, ledger, costes, cuotas, streams truncados y origen mostrado en la UI.

Ejecutar la regresión general antes de compartir el cambio. Registrar por separado las comprobaciones HTTP, el proveedor usado y las pruebas omitidas; instrucciones en [README de pruebas](./README.md).
