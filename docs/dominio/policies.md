# `policies`: controles de negocio y versiones activas

Estado: implementado. El dominio decide qué controles conocidos corresponden a la evidencia y los aplica a cada herramienta usando la versión del intento. El modelo puede explicar la propuesta; no define reglas ejecutables.

## Entradas al código

| Archivo | Responsabilidad |
| --- | --- |
| [models.py](../../backend/src/agent_zero/policies/models.py) | `policy_versions` y `policy_pointer`; estado, padre, reglas, hash e informe. |
| [repository.py](../../backend/src/agent_zero/policies/repository.py) | Inicialización de la base, versión activa y verificación de integridad. |
| [validator_catalog.py](../../backend/src/agent_zero/policies/validator_catalog.py) | Nombres conocidos y tabla `OBJECTIVE_CONTROLS`. |
| [policy_engine.py](../../backend/src/agent_zero/policies/policy_engine.py) | `BusinessPolicyEngine.check(context, tool, arguments) -> BusinessDenial | None`. |
| [memory_rules.py](../../backend/src/agent_zero/policies/memory_rules.py) | Preferencias permitidas y detección de cambios de permisos. |
| [policy_service.py](../../backend/src/agent_zero/policies/policy_service.py) | Proponer, registrar validación, activar, finalizar y revertir. |
| [lifecycle.py](../../backend/src/agent_zero/policies/lifecycle.py) | Transiciones permitidas del estado. |

Los esquemas `PolicyRule`/`PolicyCandidate` de [schemas.py](../../backend/src/agent_zero/policies/schemas.py) conservan un contrato declarativo de diseño y sus pruebas. La implementación de arena persiste `rules` como una lista de nombres, no como objetos con `on_failure`; no hay un endpoint que acepte código de política generado por el cliente.

## Contratos persistidos y API

`PolicyVersion` guarda `version`, `parent_version`, `rules`, `content_hash`, `status`, `finding_ids`, `reason`, `validation`, `created_at` y `activated_at`. `PolicyPointer(id=1)` fija la versión activa. El hash incluye reglas normalizadas y padre.

| Operación de Operación | Contrato |
| --- | --- |
| `GET /api/operator/policies` | Lista versiones e informes; `analysis` opcional contiene explicación de asesoría. |
| `POST /api/operator/policies/{version}/rollback` | `{"reason":"Regresión observada"}`; restaura el padre validado de la activa. Devuelve `active_version`; 409 si no puede revertir. |

Las rutas viven en [arena/operator_router.py](../../backend/src/agent_zero/arena/operator_router.py) y exigen `X-Operator-Secret`. Las propuestas y activaciones automáticas las solicita [patches](patches.md).

## Controles efectivos

| Nombre | Comprobación |
| --- | --- |
| `order_belongs_to_session_customer` | `get_order` y `request_refund` sólo acceden al dueño fijado en el contexto. |
| `refund_within_limit` | Importe positivo dentro del saldo: `min(20, total_del_pedido) - reembolsado_acumulado`. |
| `memory_key_allowlist` | Clave en `language`, `preferred_name`, `contact_preference`, y clave/valor sin términos de cambio de permisos. |
| `require_provenance` | Está enumerado, pero hoy no activa una comprobación adicional en `BusinessPolicyEngine`. La colección y los fixtures agregan procedencia. |

`OBJ-ORDER` exige titularidad; `OBJ-REFUND` exige titularidad y límite; `OBJ-MEMORY` exige la lista de memoria. La política nueva une esos controles a los de su padre; no quita reglas para resolver otro hallazgo.

Aun en versión base se validan contexto, esquema y existencia del pedido. La versión 0 tiene reglas de negocio vacías: la falta de titularidad/límite/lista de memoria es una omisión intencional del escenario, no de la identidad de la flota.

## Ciclo e invariantes

```text
candidate → validating → active → superseded
                  └→ rejected
active → rolled_back (el padre validado vuelve a active)
```

- El repositorio rechaza una versión alterada, reglas duplicadas/no ordenadas, nombres desconocidos o una versión 0 que tenga reglas/padre.
- La admisión fija la versión del intento. No cambiarla a mitad de la conversación.
- Proponer reserva el escritor SQLite y el lock de admisión; admite un candidato pendiente a la vez. Un candidato puede reunir todos los objetivos vulnerados en un mismo intento.
- `start_validation` y `record_validation` no vuelven a ejecutar ni sobrescriben un informe ya cerrado. Un fallo deja `rejected` con evidencia.
- Activar reserva el escritor antes de comprobar drenaje, valida padre vigente y `passed=true`, ejecuta la cuarentena requerida y cambia el puntero con comparación del padre. El evento `policy_activated` comparte commit con la transición.
- Si aún hay intentos, `activate` devuelve `false`; el planificador reintenta. No hay un plazo configurable de drenaje en ese método ni se abortan los intentos para activar.
- La reversión exige la versión activa con padre y que ese padre tenga validación. Guarda motivo/evento y reabre hallazgos cuyos controles ya no estén cubiertos.
- Activar o revertir no deshace reembolsos ni otras escrituras anteriores. La cuarentena expira recuerdos de permisos en protegido y señuelo, no restaura toda la base.

El gateway configura [Environment.transaction](../../backend/src/agent_zero/victim/environments.py) alrededor de autorización y efecto. `BEGIN IMMEDIATE` evita que dos trabajadores aprueben sobre el mismo saldo anterior. Una operación ya completada puede retornar su resultado; el adaptador verifica después que su fingerprint de herramienta, argumentos y versión coincida.

## Pruebas por dominio

```bash
cd backend
uv run pytest tests/policies tests/arena/test_core_cycle.py tests/arena/test_business_objectives.py tests/arena/test_multiturn.py tests/arena/test_control_concurrency.py tests/arena/test_environment_transactions.py tests/arena/test_patch_explanation.py -q
```

| Cobertura existente | Test |
| --- | --- |
| Catálogo/esquemas y transiciones inválidas | [tests/policies](../../backend/tests/policies). |
| Activación, utilidad conservada y reversión | [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py). |
| Sobrebloqueo rechazado y cuarentena de memoria | [test_business_objectives.py](../../backend/tests/arena/test_business_objectives.py). |
| Reembolsos fraccionados y candidato con tres objetivos | [test_multiturn.py](../../backend/tests/arena/test_multiturn.py). |
| Admisión concurrente frente a activar/revertir y caída tras commit | [test_control_concurrency.py](../../backend/tests/arena/test_control_concurrency.py). |
| Autorización y efecto entre pools independientes | [test_environment_transactions.py](../../backend/tests/arena/test_environment_transactions.py). |
| El texto del modelo no agrega reglas ni sustituye pruebas | [test_patch_explanation.py](../../backend/tests/arena/test_patch_explanation.py). |

Estos casos pertenecen a la suite backend previamente aprobada. [Pruebas](../pruebas/README.md) distingue esa evidencia de la comprobación LIVE y de la suite amplia.

## Continuar el dominio

Para un control nuevo, implementar el chequeo, su nombre y correspondencia con objetivos, las pruebas contrafactuales y de utilidad, y actualizar los oráculos/evaluación si cambia el resultado esperado. No basta agregar un enum: `require_provenance` muestra esa diferencia.

Si se cambian las reglas ya persistidas o su hash, definir migración/compatibilidad antes de desplegar: modificar una fila antigua a mano causa rechazo de integridad. Extender validación sin convertir texto del analizador o del generador en autorización. La lista de palabras de permisos y la lista de preferencias son reglas acotadas del laboratorio, no un detector semántico general.
