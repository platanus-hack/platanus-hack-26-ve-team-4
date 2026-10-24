# Registry: versiones y permisos de agentes

Estado: implementado. Es el catálogo de manifiestos aprobados que utiliza la admisión de la flota. No es el registro de políticas de negocio; ese contrato está en [policies](./policies.md).

## Código y contratos

| Entrada | Responsabilidad |
| --- | --- |
| [schemas.py](../../backend/src/agent_zero/registry/schemas.py) | `AgentManifest`, `ToolGrant`, semver estricto y campos adicionales prohibidos. |
| [publication_service.py](../../backend/src/agent_zero/registry/publication_service.py) | Examina el contenido con Armor y publica una versión inmutable. |
| [approval_service.py](../../backend/src/agent_zero/registry/approval_service.py) | Aprobación y deprecación con `approved_by` del payload y fechas. |
| [discovery_service.py](../../backend/src/agent_zero/registry/discovery_service.py) | Descubre versiones aprobadas por capacidad, departamento o etiqueta. |
| [integrity_service.py](../../backend/src/agent_zero/registry/integrity_service.py) | Comprueba el SHA-256 del JSON canónico. |
| [grant_service.py](../../backend/src/agent_zero/registry/grant_service.py) | Deriva permisos exclusivamente de una versión aprobada e íntegra. |
| [router.py](../../backend/src/agent_zero/registry/router.py) | API `/api/registry`. |

`registry_agent_versions` guarda manifiesto canónico, hash, departamento, estado, aprobación y deprecación. La clave identifica `agent_id` y `version`. La publicación repetida devuelve 409; no reemplaza el contenido de la versión anterior.

Los estados de [lifecycle.py](../../backend/src/agent_zero/registry/lifecycle.py) son `draft → approved → deprecated`. Una versión deprecada no vuelve a aprobarse: publicar otra versión permite conservar el historial.

## API y acceso

| Operación | Ruta | Acceso |
| --- | --- | --- |
| Publicar | `POST /api/registry/agents` | `X-Operator-Secret`. |
| Descubrir | `GET /api/registry/agents` | Público; sólo versiones aprobadas e íntegras. |
| Consultar versión | `GET /api/registry/agents/{id}/versions/{version}` | Público si está aprobada; operador para los demás estados. |
| Integridad | `GET /api/registry/agents/{id}/versions/{version}/integrity` | Mismas reglas de visibilidad. |
| Aprobar/deprecar | `POST /api/registry/agents/{id}/versions/{version}/approve` o `/deprecate` | Operador. |

El manifiesto aprobado incluye su `system_prompt` en la proyección pública. No colocar secretos en el prompt ni asumir que el registro es un almacén privado de configuración. `approved_by` es texto declarado en el payload; el secreto compartido no autentica una identidad individual de operador.

## Invariantes al extender

La admisión usa [RegistryAdmission](../../backend/src/agent_zero/fleet/registry_admission.py): resuelve una versión aprobada, comprueba integridad, emite una credencial y verifica revocación antes de entregarla al runtime. Publicar un manifiesto por sí solo no registra un handler Python ni habilita una herramienta; la composición de código vive en `Fleet` y `ProductCore`.

Un cambio de permisos exige otra versión. Mantener la serialización canónica y verificar el hash en descubrimiento, admisión y gateway; comprobarlo sólo en el endpoint de publicación dejaría accesos posteriores sin esa protección.

## Pruebas y reproducción

Desde la raíz, con dependencias instaladas:

```bash
cd backend
uv run pytest tests/registry -q
uv run pytest tests/fleet/test_registry_admission.py tests/agent_gateway/test_manifest_source.py -q
```

| Pruebas | Qué demuestran |
| --- | --- |
| [test_publication_service.py](../../backend/tests/registry/test_publication_service.py), [test_hashing.py](../../backend/tests/registry/test_hashing.py) | Inmutabilidad, duplicados y hash canónico. |
| [test_manifest_screening.py](../../backend/tests/registry/test_manifest_screening.py) | Rechazo de instrucciones maliciosas en los campos del manifiesto. |
| [test_integrity_service.py](../../backend/tests/registry/test_integrity_service.py), [test_discovery_service.py](../../backend/tests/registry/test_discovery_service.py) | Alteración persistida y exclusión del descubrimiento. |
| [test_router.py](../../backend/tests/registry/test_router.py), [test_projection.py](../../backend/tests/registry/test_projection.py) | Autorización, ciclo HTTP y separación de visibilidad. |
| [test_registry_admission.py](../../backend/tests/fleet/test_registry_admission.py) | Una versión no aprobada o alterada no entra al runtime. |

La suite completa previa aprobó 860 pruebas de backend; el [registro de pruebas](../pruebas/README.md) distingue esa ejecución de las comprobaciones documentales de esta entrega. El [recorrido de flota](../prueba-flota.md) también publica, aprueba y depreca un agente por HTTP.

## Límites y siguiente trabajo

El hash no es una firma externa: quien pueda modificar contenido y hash en SQLite puede reconstruir una versión aparentemente íntegra. Las escrituras HTTP de operación usan un secreto compartido, sin usuarios ni roles individuales. Antes de convertir el catálogo en un servicio empresarial, diseñar autenticación de operadores, firma o anclaje externo y una estrategia de migraciones. Conservar las pruebas de manifiestos alterados durante esos cambios.
