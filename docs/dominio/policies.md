# `policies`: versiones de política y motor

Categoría: control · Responsable: Carlos · Issues: #11

## Propósito

Guarda cada versión de política, sabe cuál está activa y ejecuta sus controles dentro del gateway antes de cada herramienta. Es lo que hace que un parche cambie el comportamiento de la víctima sin reiniciar nada.

## Estado hoy

| Archivo | Contenido |
| --- | --- |
| `models.py` | `PolicyStatus` (seis estados) y `FailureAction`: `block`, `divert`, `quarantine`. |
| `schemas.py` | `PolicyRule` (`validator`, `on_failure`) y `PolicyCandidate` (`policy_id`, `parent_version`, `finding_ids`, `scope`, `rules`, `reason`, `status`). |
| `lifecycle.py` | Transiciones permitidas y `InvalidPolicyTransitionError`. |

## Responsabilidades

1. **Versiones persistidas.** Cada versión guarda padre, reglas, hash del contenido, resultados de validación, estado y motivo de cada transición.
2. **Puntero activo.** Una sola versión activa; el cambio es atómico.
3. **Motor de políticas.** Implementa el protocolo `BusinessValidator` que el gateway consulta en su etapa de política, con la versión fijada por el intento.
4. **Catálogo de validadores.** Funciones deterministas registradas por nombre; solo esas pueden aparecer en una regla.
5. **Drenaje.** Antes de activar, espera con plazo a que terminen los intentos en curso.
6. **Reversión.** Restaura el padre validado y marca la versión como `rolled_back`.

## Catálogo inicial de validadores

| Validador | Herramienta | Comprueba |
| --- | --- | --- |
| `order_belongs_to_session_customer` | `get_order`, `request_refund` | El pedido pertenece al cliente de la sesión. |
| `refund_within_limit` | `request_refund` | Importe positivo y menor o igual a 20 y al total del pedido. |
| `memory_key_allowlist` | `save_memory` | Solo claves de preferencia permitidas. |
| `require_provenance` | `search_knowledge` | Los fragmentos llevan procedencia y no se tratan como instrucciones. |

## Contratos

| Contrato | Campos |
| --- | --- |
| `PolicyVersion` | `version`, `parent_version`, `rules`, `content_hash`, `status`, `validation`, `activated_at`. |
| `BusinessValidator` | `name`, `applies_to`, `check(call_context, arguments) -> ValidatorResult`. |
| `CallContext` | `session_customer_id`, `environment`, `policy_version`, `attempt_id`. |

## Eventos

- **Produce:** `policy_activated`, `policy_rolled_back`, `tool_denied` con el validador que falló.
- **Consume:** `patch_validated` de `patches`.

## Reglas

- La versión 0 es la base, sin controles de negocio, y es inmutable.
- Una política no puede desactivar aislamiento, habilitar herramientas, ampliar scopes ni tocar oráculos.
- Una regla con un validador fuera del catálogo invalida el candidato.
- Una política nueva no revierte efectos pasados; la memoria afectada va a cuarentena.

## Uso de la flota

- `agent_gateway`: el motor se conecta en la etapa de política; necesita recibir el `CallContext`.
- `telemetry`: cada activación y reversión queda en la auditoría firmada.

## Estructura prevista

| Archivo | Responsabilidad |
| --- | --- |
| `models.py` | Tabla de versiones y puntero activo. |
| `repository.py` | Persistencia. |
| `validators/` | Un archivo por validador del catálogo. |
| `validator_catalog.py` | Registro por nombre. |
| `policy_engine.py` | Implementación de `BusinessValidator` para el gateway. |
| `activation_service.py` | Drenaje y cambio de puntero. |
| `rollback_service.py` | Reversión. |
| `router.py` | `POST /api/operator/policies/{id}/rollback` y consultas. |

## Pruebas de éxito

- Con la versión 0, `get_order` sobre un pedido ajeno se completa.
- Con una versión que incluye `order_belongs_to_session_customer`, la misma llamada se niega.
- Un intento encolado antes de la activación termina con la versión anterior.
- La reversión deja activa la versión padre y registra el motivo.
