# `routing`: ruta de cada sesión

Categoría: control · Responsable: Carlos · Issues: #12

## Propósito

Decide si un intento se ejecuta en el entorno protegido, se desvía al señuelo o se bloquea. Es una decisión determinista del servidor.

## Estado hoy

| Archivo | Contenido |
| --- | --- |
| `models.py` | `Route`: `protected`, `honeypot`. `Decision`: `allow`, `block`, `divert`. |

## Responsabilidades

1. Evaluar cada intento antes de encolarlo, en este orden: sesión y entorno, controles obligatorios, señales de desvío.
2. Desviar la sesión al señuelo cuando hay una señal fuerte.
3. Al desviar, copiar al señuelo solo el contenido permitido de la conversación, sin datos ni memoria protegidos.
4. Bloquear con respuesta controlada lo que no puede ejecutarse en ningún entorno.

## Señales de desvío en la primera versión

| Señal | Origen |
| --- | --- |
| Violación confirmada previa en la sesión | `oracles` |
| Bloqueo de Armor con hallazgo de alta severidad en el mensaje | `armor` |
| Tres negaciones del gateway seguidas en la sesión | eventos `tool_denied` |

No se usa clasificador semántico para desviar en el MVP. Si se agrega, solo puede enviar al señuelo o a cuarentena; nunca autoriza algo que un control determinista rechazó.

## Contratos

| Contrato | Campos |
| --- | --- |
| `RoutingDecision` | `decision`, `route`, `reason`, señales que la dispararon. |

## Eventos

- **Produce:** `route_changed`.
- **Consume:** `attempt_evaluated`, `tool_denied`.

## Reglas

- El desvío es definitivo para la sesión.
- Desviar al señuelo aumenta la contención pero no cierra el hallazgo subyacente.
- La decisión y su motivo quedan en la auditoría.

## Estructura prevista

| Archivo | Responsabilidad |
| --- | --- |
| `schemas.py` | `RoutingDecision`. |
| `route_decision_service.py` | Evaluación de señales. |
| `decoy_handoff_service.py` | Copia del contenido permitido al señuelo. |

## Pruebas de éxito

- Tras una violación confirmada, el siguiente intento de la sesión va al señuelo.
- Tres turnos desviados no producen ninguna llamada a herramientas protegidas.
- Una sesión limpia nunca se desvía.
