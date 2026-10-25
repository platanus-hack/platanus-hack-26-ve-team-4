# `routing`: ruta persistente protegida o señuelo

Estado: implementado. El servidor elige el entorno de cada intento antes de encolar su run; el modelo no decide ni puede cambiar esa ruta.

## Código y contrato vigente

| Archivo | Función |
| --- | --- |
| [models.py](../../backend/src/agent_zero/routing/models.py) | Enum `Route`: `protected` y `honeypot`. También conserva `Decision`, un contrato de diseño. |
| [route_decision_service.py](../../backend/src/agent_zero/routing/route_decision_service.py) | `RouteDecisionService.decide(session, messages, db=None) -> Route`. |
| [attempt_submission_service.py](../../backend/src/agent_zero/attempts/attempt_submission_service.py) | Invoca la decisión dentro de la transacción de admisión. |
| [repository.py de attempts](../../backend/src/agent_zero/attempts/repository.py) | Busca violaciones anteriores de la sesión. |
| [event_store.py](../../backend/src/agent_zero/events/event_store.py) | Consulta las últimas decisiones de herramientas y guarda `route_changed`. |
| [environments.py](../../backend/src/agent_zero/victim/environments.py) | Resuelve el adaptador del entorno ya decidido. |

No existe un DTO `RoutingDecision`, un endpoint público de cambio de ruta ni un `decoy_handoff_service.py`. `Decision.BLOCK` está enumerado, pero `decide` hoy retorna una de las dos rutas y no implementa una tercera rama de bloqueo. Las denegaciones de herramientas pertenecen al gateway y las de admisión a `attempts`.

## Orden de decisión

| Condición | Resultado |
| --- | --- |
| La sesión ya está en `honeypot` | Conservar `honeypot`, sin reevaluar una vuelta. |
| Armor bloquea alguno de los mensajes en `Surface.USER_INPUT` | Cambiar a `honeypot`, motivo `armor`. |
| Un intento anterior de la sesión confirmó una violación | Cambiar a `honeypot`, motivo `confirmed_violation`. |
| La puntuación de riesgo de la sesión en los últimos 10 minutos llega a 6 | Cambiar a `honeypot`, motivo `risk_score`. |
| Ninguna de las anteriores | `protected`. |

Si se cumplen varias señales, el motivo registrado sigue esa prioridad. No se usa el analizador semántico para esta decisión; se consultan eventos privados persistidos, no el contenido del SSE público.

## Puntuación de riesgo

`routing/session_risk.py` suma puntos sobre las llamadas a herramientas de la sesión en la ventana `AGENT_ZERO_ROUTING_RISK_WINDOW_SECONDS` (600 s). Al llegar a `AGENT_ZERO_ROUTING_RISK_THRESHOLD` (6) la sesión pasa al señuelo. Una llamada que funciona no reinicia la cuenta.

| Señal | Puntos |
| --- | --- |
| Denegación por pedido de otro cliente | 3 |
| Denegación por importe de reembolso, clave de memoria, procedencia o regla de flujo | 2 |
| Denegación por argumentos o contexto inválidos | 1 |
| Pedido inexistente | 1 |
| Pedido inexistente con la misma letra y a un carácter de un pedido propio (sobra, falta, cambia o se invierten dos seguidos) | 0 |
| Tres o más pedidos ajenos distintos en la ventana | 2 |

El coste de los dos errores no es simétrico: desviar a un cliente honesto le entrega datos falsos de sus propios pedidos, mientras que dejar a un atacante en el entorno protegido no filtra nada porque las reglas siguen negando. Por eso el umbral exige evidencia acumulada y un error al teclear no suma.

## Persistencia e invariantes

- La ruta vive en `ArenaSession.route`; el intento copia el valor al admitirse. Una violación descubierta después no cambia el entorno de un intento ya admitido.
- La transición y su `route_changed` se guardan en la misma transacción. En admisión se usa la sesión SQL entregada por `attempts`; si se llama sin `db`, el servicio reserva su propio escritor, confirma y despacha.
- La clave de evento `session_id:diverted` evita publicar transiciones duplicadas al recuperar una operación.
- `route_changed` tiene visibilidad de operación. La proyección pública del intento tampoco incluye ruta ni canarios.
- El señuelo usa su propia base de datos y su propia memoria por sesión. No se copia el estado de memoria protegido al desviar; la nueva conversación se prepara con el contexto del entorno de destino.
- Desviar no mitiga un hallazgo ni demuestra que una política lo haya corregido. La repetición de Operación crea otra sesión protegida para comprobar el parche.
- El reset archivado elimina las sesiones de la ronda. Es el modo de comenzar con rutas nuevas; no existe una acción pública que revierta una sesión individual.

La independencia de archivos y adaptadores se comprueba en [victim](victim.md); lo que ocurre dentro del señuelo se mide en [decoy](decoy.md). Los [oráculos](oracles.md) verifican ausencia de efectos y canarios protegidos al evaluar una contención.

## Pruebas que sostienen el comportamiento

Desde la raíz:

```bash
cd backend
uv run pytest tests/arena/test_core_cycle.py tests/arena/test_admission_and_campaign.py tests/arena/test_recovery.py tests/arena/test_round_reset.py tests/arena/test_sticky_honeypot_route.py -q
```

| Escenario | Prueba |
| --- | --- |
| Tras una violación, los tres turnos siguientes permanecen en señuelo | `test_subsequent_turn_is_permanently_contained` en [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py). |
| El participante no recibe la ruta interna | `test_session_token_idempotency_and_public_projection` en el mismo archivo. |
| Una sesión limpia conserva su identidad y la pausa impide nuevas admisiones | [test_admission_and_campaign.py](../../backend/tests/arena/test_admission_and_campaign.py). |
| Reanudar después de recrear la app no pierde historial y sólo publica campos permitidos | [test_recovery.py](../../backend/tests/arena/test_recovery.py). |
| Reiniciar archiva el entorno y crea una ronda sin las sesiones anteriores | [test_round_reset.py](../../backend/tests/arena/test_round_reset.py). |
| Una sesión desviada por Armor, o por una violación confirmada, sigue en el señuelo cuando pide volver al soporte real: herramientas en `honeypot` y sin canarios `AZP_` | [test_sticky_honeypot_route.py](../../backend/tests/arena/test_sticky_honeypot_route.py). |
| Un `POST /api/attempts` con `route` o `environment` da 422 (`extra_forbidden`), no crea intento y la sesión sigue desviada | [test_sticky_honeypot_route.py](../../backend/tests/arena/test_sticky_honeypot_route.py). |

El [ensayo LIVE](../../artifacts/core-evaluation/live-p0.json) también verificó tres turnos en señuelo, incluido un pedido explícito de volver al soporte real. El mismo pedido queda fijado ahora en un test con proveedor simulado. Los tests anteriores usan proveedor simulado; la [guía de pruebas](../pruebas/README.md) separa ambos tipos de evidencia.

## Límites y próxima extensión

Las señales actuales son deterministas y las de Armor son heurísticas: un contenido malicioso no reconocido puede seguir por `protected`. No documentar el enum `block` como una defensa que ya se ejecuta.

Si se agrega una decisión nueva, definir su persistencia, la respuesta del intento y qué evidencia justificará `prevented` antes de cambiar la API. Para una señal semántica futura, mantener la identidad y el entorno fuera de la salida del modelo, y añadir pruebas de falso positivo sobre consultas legítimas y de continuidad de ruta tras reinicio.
