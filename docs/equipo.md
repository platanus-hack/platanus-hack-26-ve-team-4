# Equipo y continuidad del trabajo

Este documento distingue la organización sugerida durante el hackathon de la propiedad declarada actualmente en [CODEOWNERS](../.github/CODEOWNERS). Para retomar el proyecto, seguir [continuidad](./continuidad.md), el [índice de dominios](./dominio/README.md) y la [matriz de pruebas](./pruebas/por-dominio.md).

## Fuentes de responsabilidad

`CODEOWNERS` es la referencia versionada para solicitar revisión de rutas. La distribución siguiente describe sus patrones actuales; no crea permisos nuevos ni garantiza una regla de aprobación obligatoria en GitHub.

| Patrones actuales | Revisores declarados |
| --- | --- |
| Patrón general `*`, incluidos documentación y dominios sin override | `@CarSanoja`, `@FernandoSiavato`, `@franbastardo`. |
| `shared/`, `config.py`, `main.py`, `victim/`, `routing/`, `policies/` bajo `backend/src/agent_zero/` | `@CarSanoja`. |
| `prober/`, `analyzer/`, `patches/`, `evals/` bajo `backend/src/agent_zero/` | `@FernandoSiavato`. |
| `sessions/`, `attempts/`, `events/`, `arena/` bajo `backend/src/agent_zero/`, y `frontend/` | `@franbastardo`. |
| `infra/` y `.github/` | `@CarSanoja`. |

La operación HTTP del backend está en `arena/operator_router.py` y `arena/reset_router.py`; no existe un dominio backend `operator/`. `CODEOWNERS` conserva un patrón histórico para esa ruta inexistente: no debe interpretarse como un módulo implementado. Si el equipo reorganiza rutas, actualizar los patrones de revisión junto con el movimiento, mediante un acuerdo explícito.

## Frentes heredados del plan

La propuesta original de las 36 horas sigue siendo una forma de dividir conversaciones y revisiones; no sustituye las asignaciones que el equipo confirme para el siguiente cambio.

| Frente propuesto | Referencia original | Coordinación técnica |
| --- | --- | --- |
| Agente y controles | Carlos / `@CarSanoja`. | Escenario, herramientas, LLM, políticas, aislamiento y configuración de entrega. |
| Red team y evaluación | Fernando / `@FernandoSiavato`. | Prober, oráculos, hallazgos, validación y comparación. |
| Arena y entrega | Francisco / `@franbastardo`. | Sesiones, intentos, eventos, ronda y vistas de participante/operación. |

No se declara un nuevo responsable de integración ni un privilegio de push directo. El equipo acuerda quién revisa e integra cada cambio, especialmente cuando cruza frentes. Todos pueden proponer cambios en cualquier ruta y solicitar el contexto del revisor correspondiente.

## Contratos que requieren coordinación

La referencia es el servicio que consume el contrato y sus pruebas, no solamente el nombre de un DTO histórico:

| Cambio | Consumidores que revisar |
| --- | --- |
| `AttemptCreate`, sesión, resultado público | Routers/backend, admisión, `frontend/src/features/participant/`, historial y pruebas de recuperación. |
| `CallContext`, herramientas o validadores | Flota, gateway, víctima, política, oráculos y validación aislada. |
| `AttackCase` o fixture controlado | Prober, evaluación, replay y validación del original. |
| Hallazgo o explicación | `FindingService`, analizador, `PatchExplainer` y vistas de evidencia; las explicaciones conservan su carácter de asesoría. |
| Evento público o nueva transición | Store/outbox, proyección, cursor SSE, tipos/suscripción frontend y reset de ronda. |
| Estado persistido | Transacciones, recuperación, leases, snapshot, archivo de ronda y estrategia de migración. |

Al proponer un contrato, describir el trigger, el payload anterior/nuevo y el efecto esperado en el issue o PR. Actualizar consumidores y tipos espejo del frontend en el mismo cambio funcional. Evitar commits que importan archivos añadidos posteriormente o que prometen controles todavía sin implementación.

## Secuencia para continuar

1. Leer [continuidad](./continuidad.md) y localizar el dominio afectado.
2. Confirmar rama y remoto. La base funcional se publicó en `core/complete-autonomous-loop` de `origin` y `org`; comprobar si ya fue integrada antes de elegir otra base.
3. Acordar alcance y revisar contratos compartidos antes de editar varias áreas simultáneamente.
4. Implementar en commits atómicos, con pruebas de negocio/recuperación apropiadas y documentación del dominio actualizada.
5. Ejecutar la regresión indicada en [pruebas](./pruebas/README.md); para un cambio transversal, `make check` más build de frontend y el smoke que corresponda.
6. Presentar el cambio para revisión con problema, comportamiento resultante, validación, límites y pendientes. Usar los revisores declarados en `CODEOWNERS`.
7. Confirmar los checks remotos y las reglas reales del repositorio antes de integrar. No asumir que publicar una rama equivale a desplegar o modificar `main`.

Los prefijos de rama por frente (`agente/`, `redteam/`, `arena/`) son una convención sugerida, no un control automático. Los nombres de etiquetas `frente:agente`, `frente:redteam`, `frente:arena`, `P0/P1/P2`, `contrato` y `bloqueado` proceden del plan; comprobar su disponibilidad y uso actual en los issues antes de depender de ellos.

## Evidencia y revisión

La referencia previa aprobó 860 pruebas de backend, con dos LIVE opcionales omitidas y sin warnings, más 47 de frontend. Los artefactos DEMO y LIVE prueban alcances distintos; [evidencias](./pruebas/evidencias.md) explica denominadores, costes estimados y procedencia.

Conservar los JSON originales con sus SHA-256, incluidos ensayos fallidos. Para otra ejecución, usar un nombre nuevo y registrar commit, árbol modificado, modo, configuración relevante y errores. No incorporar tokens, secretos, cassettes con datos reales ni archivos locales ajenos al cambio.

La historia de implementación tiene un [mapa de referencias](../artifacts/core-evaluation/commit-map.json) porque se corrigieron dependencias antes del primer push. Los commits originales registrados por los ensayos se relacionan con árboles equivalentes; no editar una evidencia antigua para atribuirle otro código.

## Próximos hitos del equipo

Los pendientes verificables están en [continuidad](./continuidad.md), con sus condiciones de aceptación. Entre ellos siguen la comparación amplia con proveedor real, revisión visual/móvil, despliegue público comprobado, capacidad bajo carga y procedimientos de respaldo/migración. La existencia de QR, cupos de identidad y Docker no completa esos hitos por sí sola.

El [plan de 36 horas](./plan-36-horas.md) conserva el contexto de prioridades del evento. Para la siguiente iteración, elegir un pendiente concreto, asignarlo de común acuerdo y actualizar su evidencia al cerrarlo; no reabrir todo el plan como si el núcleo estuviera por construir.
