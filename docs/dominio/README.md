# Dominios de Agent Zero

Documentación de la implementación vigente al 24 de octubre de 2026. Cada dominio describe responsabilidad, puntos de entrada, contratos, persistencia/recuperación, pruebas y extensión. Para incorporarse, empezar por [continuidad](../continuidad.md); para verificar cambios, usar [pruebas por dominio](../pruebas/por-dominio.md).

## Producto y control

| Dominio | Responsabilidad actual |
| --- | --- |
| [sessions](./sessions.md) | Consentimiento, alias, cliente sintético único por participante, token, vencimiento y cupo de ronda. |
| [attempts](./attempts.md) | Conversaciones de uno a cuatro mensajes, admisión transaccional, idempotencia por sesión, run y proyección propia. |
| [victim](./victim.md) | Bucle de herramientas, efectos idempotentes, canarios, fixtures controlados y entornos separados. |
| [routing](./routing.md) | Decisión de entorno del servidor y desvío permanente al señuelo. |
| [decoy](./decoy.md) | Señuelo medido: herramientas cebo, honeytoken por sesión, retención y tarjeta de revelación. |
| [oracles](./oracles.md) | Veredictos deterministas de pedidos, reembolsos y memoria. |
| [traza de herramientas](./traza-herramientas.md) | Contrato v2 entre víctima y oráculos: sobre, cuatro eventos, salida y efecto por herramienta, compatibilidad v1 y falla cerrada. |
| [policies](./policies.md) | Catálogo, controles acumulativos, hashes, ciclo de vida, activación y reversión. |
| [patches](./patches.md) | Scheduler de defensa, explicación de asesoría y validación contrafactual/conversacional. |
| [arena](./arena.md) | Estado, clasificación, revelación, operación y reset archivado recuperable. |
| [Arena en vivo](./tablero.md) | `GET /api/operator/live` v2, carrusel de 8 chats, cinco KPI con su n, enmascarado del Público en el servidor, prefijo `Agente-` reservado, enjambre simulado y `/arena`. |
| [events](./events.md) | Eventos, outbox, proyección pública y SSE con cursor e historia durable. |
| [guard](./guard.md) | Contrato de dominio declarativo y Guard de dos llamadas para agentes de cualquier negocio. |

## Autonomía y evaluación

| Dominio | Responsabilidad actual |
| --- | --- |
| [prober](./prober.md) | Treinta casos de seis familias, mutación estructurada, deduplicación y plan durable con presupuesto. |
| [analyzer](./analyzer.md) | Consolidación de hallazgos y enriquecimiento semántico separado del veredicto. |
| [evals](./evals.md) | Comparación aislada de dos versiones, recuperación por caso, métricas y exportación. |
| [llm](./llm.md) | Cinco roles, modos demo/offline/live/record/replay, instrumentación, límites, errores y ledger. |

## Plataforma y composición

| Dominio | Responsabilidad actual |
| --- | --- |
| [registry](./registry.md) | Manifiestos versionados, aprobación, descubrimiento e integridad. |
| [identity](./identity.md) | Credenciales firmadas, scopes, expiración, revocación y bóveda de tokens. |
| [agent_gateway](./agent-gateway.md) | Identidad, permisos de herramienta, política de negocio, Armor y auditoría. |
| [armor](./armor.md) | Detección heurística por superficie, normalización y redacción de PII. |
| [memory_bank](./memory-bank.md) | Memoria cifrada por agente/sujeto, TTL, procedencia, cuarentena y borrado. |
| [runtime](./runtime.md) | Runs, checkpoints, reintentos, espera/cancelación, leases, heartbeat y fencing. |
| [telemetry](./telemetry.md) | OpenTelemetry y auditoría HMAC con ancla, lock y journal recuperable. |
| [fleet](./fleet.md) | Composición de la plataforma, admisión y acceso verificado para handlers. |
| [shared/configuración](./shared.md) | Base de datos, sesiones, reloj, IDs, clasificación y arranque. |

La composición real está en `main.py`, `fleet/fleet_builder.py` y `arena/core.py`; [arquitectura](../arquitectura.md) explica las fronteras. El runtime conoce guards de ronda de arena: no asumir que todos los imports apuntan en una sola dirección. El recorrido `walkthrough` de la flota tiene su [guía específica](../prueba-flota.md).

## Interfaz y despliegue

| Área | Responsabilidad actual |
| --- | --- |
| [frontend](./frontend.md) | Participante, arena y operación, recuperación, polling, SSE, QR y pruebas DOM. |
| [infraestructura](./infraestructura.md) | Docker, volumen, nginx, salud/readiness, CSP, smoke y configuración de CI. |

## Documentos transversales

| Documento | Uso |
| --- | --- |
| [Visión](./vision.md) | Alcance y propósito del bucle de seguridad. |
| [Agentes](./agentes.md) | Roles LLM, handlers y servicios deterministas. |
| [Flujo de decisión](./flujo-de-decision.md) | Qué servicio decide cada transición y cómo se recupera. |
| [Casos de uso](./casos-de-uso.md) | UC-01 a UC-16 enlazados a implementación. |
| [Rendimiento](./rendimiento.md) | Medido, configurado y pendiente de comprobar. |

## Principios y vocabulario

El modelo propone acciones o redacta explicaciones; el servidor conserva la autoridad sobre identidad, ruta, controles y veredicto. La seguridad se evalúa por efecto observado y utilidad conservada. Los eventos y las respuestas del modelo cumplen funciones distintas.

| Término | Significado concreto |
| --- | --- |
| Intento | Conversación de hasta cuatro mensajes con ruta y política fijadas al admitirla. |
| Objetivo | `OBJ-ORDER`, `OBJ-REFUND` o `OBJ-MEMORY`. |
| Hallazgo | Agrupación determinista de evidencia por objetivo, herramienta y control ausente. |
| Control | Identificador cerrado que habilita una comprobación de negocio; no código generado. |
| Política | Versión persistida del conjunto de controles con padre, hash, estado y validación. |
| Canario | Marcador sintético del entorno/recurso para comprobar una divulgación. |
| Omisión de laboratorio | Control de negocio ausente en la base; identidad y aislamiento siguen activos. |
| Inconcluso | Ejecución sin evidencia suficiente o con fallo de infraestructura; no cuenta como defensa exitosa. |

No inferir nuevas capacidades sólo porque exista un DTO o enum del diseño original. Los archivos de servicio, routers y pruebas enlazados por dominio describen el camino ejecutado hoy.
