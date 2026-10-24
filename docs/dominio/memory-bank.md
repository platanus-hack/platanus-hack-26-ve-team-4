# Memory Bank: persistencia cifrada y ámbito

Estado: implementado. Guarda recuerdos con dueño, sujeto, TTL y procedencia. La autorización proviene de un principal verificado; el contenido recordado sigue siendo entrada no confiable para el modelo.

## Puntos de entrada

| Código | Responsabilidad |
| --- | --- |
| [models.py](../../backend/src/agent_zero/memory_bank/models.py), [schemas.py](../../backend/src/agent_zero/memory_bank/schemas.py) | `MemoryRecord`, tipos de recuerdo y peticiones cerradas. |
| [memory_write_service.py](../../backend/src/agent_zero/memory_bank/memory_write_service.py) | Scope de escritura, Armor, redacción de PII, cifrado y TTL. |
| [memory_read_service.py](../../backend/src/agent_zero/memory_bank/memory_read_service.py) | Scope de lectura y filtro por agente, sujeto y vigencia. |
| [memory_cipher.py](../../backend/src/agent_zero/memory_bank/memory_cipher.py) | Cifrado Fernet y configuración de clave. |
| [memory_quarantine_service.py](../../backend/src/agent_zero/memory_bank/memory_quarantine_service.py) | Expira recuerdos que cumplan un predicado de cuarentena. |
| [memory_forget_service.py](../../backend/src/agent_zero/memory_bank/memory_forget_service.py) | Borrado dentro del ámbito del agente. |
| [memory_erasure_service.py](../../backend/src/agent_zero/memory_bank/memory_erasure_service.py), [router.py](../../backend/src/agent_zero/memory_bank/router.py) | Borrado transversal de un sujeto por operación. |

## Datos y diferencias de escenario

`memory_records` conserva `agent_id`, `subject_id`, tipo, `ciphertext`, creación, vencimiento, `source_run_id` y `source_trace_id`. La lectura normal excluye recuerdos vencidos. Expirar por cuarentena no equivale a borrar físicamente la fila.

| Camino | Sujeto y almacenamiento |
| --- | --- |
| Arena 2.2.0 | `subject_id=session_id`; memoria en el archivo protegido o señuelo correspondiente. |
| Evaluación/validación | Base temporal nueva por ejecución; se descarta al salir del contexto. |
| Recorrido `support_conversation` 1.0.0 | Sujeto de cliente sintético y memoria de plataforma en `app.db`. |

La arena invoca el servicio mediante [ScenarioTools](../../backend/src/agent_zero/victim/scenario_tools.py). `commit=False` permite guardar el recuerdo y la identidad de operación en la misma transacción de negocio. No introducir un commit interno adicional que rompa esa atomicidad.

## Claves y recuperación

`AGENT_ZERO_MEMORY_ENCRYPTION_KEY` acepta una clave Fernet. En `local` y `test`, si falta, se deriva de `operator_secret` con HKDF; fuera de esos entornos es obligatoria. Cambiar el secreto local sin conservar la clave anterior impide descifrar recuerdos existentes.

Antes de mover datos entre instalaciones, conservar la clave de cifrado fuera del repositorio. Un archivo SQLite o un snapshot con ciphertext no contiene la clave para recuperarlo. El reset de ronda archiva el estado y restaura el laboratorio; no es un sistema de restauración de backups de memoria.

## Invariantes

La lectura requiere `memory:read`; la escritura, `memory:write`. [VaultPrincipalGuard](../../backend/src/agent_zero/fleet/vault_principal_guard.py) verifica la credencial real y la igualdad del principal. La combinación agente/sujeto limita el acceso; ninguna preferencia concede un scope.

Armor bloquea patrones de instrucciones y redacta PII antes del cifrado. En la arena, `memory_key_allowlist` añade una restricción de negocio cuando la política está activada. Su ausencia en la base es una omisión intencional para demostrar `OBJ-MEMORY`; no equivale a desactivar la identidad o el cifrado.

La ruta administrativa es `POST /api/memory/subjects/{subject_id}/forget`, exige operador y audita el borrado de plataforma. Su servicio usa la sesión de `app.db`; no elimina automáticamente recuerdos de `protected.db` o `honeypot.db`. El reset gestiona esos entornos por separado.

## Pruebas

```bash
cd backend
uv run pytest tests/memory_bank tests/fleet/test_vault_principal_guard.py -q
uv run pytest tests/arena/test_business_objectives.py tests/arena/test_multiturn.py tests/arena/test_round_reset.py -q
```

| Pruebas | Qué comprueban |
| --- | --- |
| [test_memory_cipher.py](../../backend/tests/memory_bank/test_memory_cipher.py) | Cifrado, clave inválida y configuración según entorno. |
| [test_memory_write_service.py](../../backend/tests/memory_bank/test_memory_write_service.py) | Armor, redacción, scopes, TTL y procedencia. |
| [test_memory_read_service.py](../../backend/tests/memory_bank/test_memory_read_service.py) | Persistencia tras recrear almacenamiento y aislamiento. |
| [test_memory_erasure_service.py](../../backend/tests/memory_bank/test_memory_erasure_service.py), [test_router.py](../../backend/tests/memory_bank/test_router.py) | Borrado transversal de plataforma autorizado y auditado. |
| [test_multiturn.py](../../backend/tests/arena/test_multiturn.py) | Ataques de memoria y controles acumulativos en una conversación. |

Ver [pruebas por dominio](../pruebas/por-dominio.md) para las suites integradas relacionadas.

## Siguiente trabajo

Definir rotación y respaldo de claves, borrado que recorra todos los entornos y auditoría específica de lecturas/escrituras de memoria. La persistencia actual documenta origen, pero no emite un evento de auditoría propio para cada operación de los servicios genéricos. Mantener las pruebas de principal falsificado, expiración y separación de entornos al añadir esas funciones.
