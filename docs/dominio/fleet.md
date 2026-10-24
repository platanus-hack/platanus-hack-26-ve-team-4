# Fleet: composición de la plataforma

Estado: implementado. `Fleet` conecta las primitivas de seguridad y runtime; `ProductCore` añade el escenario y los workers del producto. Esta separación permite conservar el recorrido de flota 1.0.0 junto con la arena 2.0.0.

## Entradas reales

| Archivo | Función |
| --- | --- |
| [fleet_builder.py](../../backend/src/agent_zero/fleet/fleet_builder.py) | Dataclass `Fleet` y composición mediante `build_fleet(settings, database, clock, telemetry)`. |
| [tables.py](../../backend/src/agent_zero/fleet/tables.py) | Creación de tablas base de registry, memoria, revocaciones, runs y leases. |
| [registry_admission.py](../../backend/src/agent_zero/fleet/registry_admission.py) | Versión aprobada/íntegra → credencial no revocada. |
| [gateway_tool_access.py](../../backend/src/agent_zero/fleet/gateway_tool_access.py) | `ToolAccess` ligado a un principal de la bóveda. |
| [vault_principal_guard.py](../../backend/src/agent_zero/fleet/vault_principal_guard.py) | Identidad verificada para los servicios de memoria. |
| [router.py](../../backend/src/agent_zero/fleet/router.py) | Estado, trazas de memoria y auditoría por API de operación. |
| [main.py](../../backend/src/agent_zero/main.py), [arena/core.py](../../backend/src/agent_zero/arena/core.py) | Ciclo de vida y composición del producto. |

`Fleet.start()` arranca `RunWorker`; `Fleet.stop()` lo drena y apaga la telemetría que posee. `ProductCore` gestiona aparte `AttemptWorker` y los entornos del escenario. El cierre de la app debe coordinar ambos antes de disponer motores.

## API y contratos

`GET /api/fleet/status`, `/api/fleet/runs/{run_id}/trace` y `/api/fleet/audit` exigen `X-Operator-Secret`. El estado enumera herramientas y handlers registrados, no concede permiso para ejecutarlos. Las trazas consultables requieren exportador `memory`.

Una nueva herramienta requiere código registrado y grant en manifiesto. Un handler nuevo requiere registro y una identidad aprobada. El registro de manifiestos no instala extensiones desde la red. Un principal creado manualmente no sustituye el acceso verificado de la flota.

## Pruebas

```bash
cd backend
uv run pytest tests/fleet tests/walkthrough -q
```

[test_fleet_scenario.py](../../backend/tests/fleet/test_fleet_scenario.py) conecta registro, admisión, memoria, herramientas, runtime y auditoría. [test_fleet_app.py](../../backend/tests/fleet/test_fleet_app.py) y [test_router.py](../../backend/tests/fleet/test_router.py) cubren el cableado real y sus endpoints. Los tests de bóveda y guard impiden usar identidades modificadas.

El [recorrido de flota](../prueba-flota.md) ejecuta 22 comprobaciones HTTP y tiene [evidencia guardada](../pruebas/evidencias.md). Usar un directorio de datos nuevo porque el recorrido revoca un agente y utiliza IDs fijos.

## Continuidad

Revisar las dependencias al extraer un servicio: el runtime conoce guards de ronda de arena y varios servicios consumen contratos de otros dominios. No asumir un grafo estrictamente unidireccional. En pruebas inyectar reloj, handlers o proveedor por las fronteras existentes; conservar el camino de admisión/gateway en las pruebas de integración.
