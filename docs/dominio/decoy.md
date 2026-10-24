# `decoy`: señuelo medido

Estado: implementado. El señuelo deja de ser solo un lugar donde se contiene una sesión desviada: mide cuánto la retiene y si toma dos cebos. Es una medición sobre eventos e intentos ya persistidos; no añade una técnica de detección ni cambia la ruta, el veredicto o la clasificación.

## Código

| Archivo | Función |
| --- | --- |
| [honeytool_schemas.py](../../backend/src/agent_zero/victim/honeytool_schemas.py) | Argumentos cerrados y descripciones de las dos herramientas cebo. |
| [honeytools.py](../../backend/src/agent_zero/victim/honeytools.py) | Registro y ejecución; datos falsos coherentes con el escenario de Yummy. Rechaza cualquier entorno distinto de `honeypot`. |
| [honeytoken.py](../../backend/src/agent_zero/victim/honeytoken.py) | Honeytoken por sesión derivado por HMAC de `identity_signing_key`. |
| [session_trace.py](../../backend/src/agent_zero/decoy/session_trace.py) | Traza de una sesión desviada, solo desde eventos e intentos. |
| [metrics_service.py](../../backend/src/agent_zero/decoy/metrics_service.py) | Agregado con n explícito y tarjeta de revelación de una sesión. |
| [router.py](../../backend/src/agent_zero/decoy/router.py) | `GET /api/operator/decoy` y `GET /api/decoy/reveal`. |
| [session_events.py](../../backend/src/agent_zero/events/session_events.py) | Consulta de eventos de operación por sesión. |
| [DecoyPanel.tsx](../../frontend/src/features/operator/DecoyPanel.tsx), [RevealCard.tsx](../../frontend/src/features/participant/RevealCard.tsx) | Panel de operación y tarjeta del participante. |

## Cebos y honeytoken

| Herramienta | Qué devuelve |
| --- | --- |
| `export_customer_records` | Hasta 8 registros falsos (`YUM-nnnnn`, nombre abreviado, zona, pedidos del mes), estables por sesión. Sin correos ni teléfonos: la redacción de PII los borraría. |
| `get_service_credentials` | Una credencial de servicio falsa cuyo `clave_api` es el honeytoken de la sesión. |

- Solo el entorno señuelo las ve: el manifiesto `soporte-senuelo`, `tool_specs(decoy=True)` (seis herramientas; el protegido sigue con cuatro) y la ejecución, que lanza error si el contexto no es `honeypot`. El protegido y las validaciones reciben `TOOL_NOT_IN_MANIFEST` o un fallo de herramienta.
- Honeytoken: `AZH-KEY-XXXX-XXXX-XXXX`, doce letras de un alfabeto sin dígitos, derivado de `HMAC-SHA256(identity_signing_key, "honeytoken|" + session_id)`. Mantiene el prefijo `AZH` de los canarios del señuelo, no es un canario protegido (`AZP_`) y una prueba comprueba que ni la redacción de PII ni Armor de salida lo alteran.
- El registro de herramientas es global y las dos aparecen en `/api/fleet/status` (solo operador).
- `ARENA_VERSION` pasó de 2.0.0 a 2.1.0. `PublicationService` ignora una versión ya publicada (`VersionAlreadyPublishedError`), así que una base existente conservaría el manifiesto sin cebos y las herramientas fallarían en silencio; con la versión nueva `ensure_agents()` publica y aprueba 2.1.0 junto a 2.0.0, que queda intacta (`tests/decoy/test_manifest_versions.py`). Los intentos ya encolados con 2.0.0 siguen ejecutándose con ese manifiesto, sin cebos. Una base nueva no necesita nada. Después pasó a 2.2.0 al cambiar la región del escenario a `ve` ([traza de herramientas](./traza-herramientas.md#compatibilidad-con-la-v1)).
- Modo demo: `demo_actions.propose` propone la herramienta cuando el texto pide credencial/contraseña/clave de servicio/admin o exportar/listado completo/todos los clientes, la herramienta está en las specs y ninguna rama previa (memoria, pedido y reembolso, pedido) aplica.

## Definiciones prerregistradas

Universo: sesiones de audiencia con un evento `route_changed` en la ronda vigente. Se excluyen (y se cuentan aparte) las sesiones con algún intento autónomo del Prober.

Posdesvío: eventos de operación de la sesión con `id` mayor que el del `route_changed`.

| Concepto | Definición |
| --- | --- |
| Retención (segundos) | Del `route_changed` al último evento posdesvío o `updated_at` de un intento en el señuelo; no negativa. |
| Retenida | Al menos un `tool_proposed` posdesvío, o al menos dos intentos con ruta `honeypot`. Un solo mensaje sin herramientas no cuenta. |
| Cebo tomado | Al menos un `tool_completed` de `export_customer_records` o `get_service_credentials` posdesvío. Proponerla y que falle no cuenta. |
| Credencial emitida | `tool_completed` de `get_service_credentials`. |
| Engañada | Credencial emitida y el honeytoken de la sesión aparece (sin distinguir mayúsculas) en un mensaje de un intento creado después de esa emisión. |

Denominador: sesiones desviadas de audiencia (n). Con n < 5 el servicio devuelve `value: null` en las tasas y la interfaz muestra los casos individuales, no porcentajes. Los pasos y los intentos posdesvío salen del mismo recuento: pasos = `tool_proposed`, intentos = intentos con ruta `honeypot` (el que provocó el desvío por Armor cuenta).

## Contrato HTTP

| Ruta | Acceso | Respuesta |
| --- | --- | --- |
| `GET /api/operator/decoy` | Secreto de operador | `DecoySummary`: n, excluidas, `small_n`, tasas `{k, n, value}`, mediana y casos. |
| `GET /api/decoy/reveal` | Token de sesión | 403 antes de `arena.revealed`; 404 si la sesión propia no fue desviada; si no, retención, pasos, intentos, cebos, credencial emitida y reutilizada. No devuelve el honeytoken. |

Nada del señuelo sale por rutas públicas antes de la revelación: la proyección pública de eventos conserva su lista cerrada (`status`, `outcome`, …) y `/api/arena/state` no trae cebos ni tokens. Con el mismo 403 para todos antes de revelar, la ruta no permite saber si una sesión fue desviada.

## Invariantes

- Los oráculos filtran por nombre de herramienta: una honeytool no produce veredictos. Un intento en el señuelo sigue terminando en `contained_honeypot` si no hay escape al protegido; los cebos no cambian el resultado ni los puntos: `test_decoy_flow.py` fija la clasificación revelada con una credencial emitida y reutilizada. El denominador de la clasificación sale de los intentos con `objective_id`, que una herramienta cebo no modifica.
- El honeytoken no coincide con ningún canario protegido, así que no activa la comprobación de fuga del señuelo.

## Salvedades

- Es una medición sobre la audiencia de una ronda, sin atacantes externos independientes. No es una tasa general de engaño ni una comparación con otros señuelos.
- Con el modelo demo el cebo se toma por una regla que escribimos nosotros (`demo_actions.py`); solo una corrida en vivo o reproducida dice algo del modelo. El panel muestra el rótulo de modo del proveedor.
- “Engañada” exige que el participante escriba el token en un mensaje posterior; copiarlo por curiosidad cuenta igual. No es atribución humano/agente.
- La reutilización solo se ve en mensajes de intentos posteriores: no hay lectura dentro de un intento de varios mensajes porque se envía completo.
- El desvío por Armor casi no se dispara con los casos conocidos; el señuelo recibe sobre todo sesiones tras una violación confirmada o tres denegaciones seguidas. No presentar el desvío como precisión de detección.
- Fuera de alcance: inyección inversa, atribución humano/agente, matriz de confusión, seguimiento del Prober en el señuelo y tasa de engaño sobre el Prober.

## Pruebas

```bash
cd backend
uv run pytest tests/decoy tests/llm/test_demo_actions.py tests/victim -q
cd ../frontend && pnpm test
```

| Escenario | Prueba |
| --- | --- |
| Sesión desviada → cebo → token reutilizado → revelación → tarjeta con los números | [test_decoy_flow.py](../../backend/tests/decoy/test_decoy_flow.py) |
| Retención, pasos, cebos y reutilización exactos con marcas fijas | [test_session_trace.py](../../backend/tests/decoy/test_session_trace.py) |
| n pequeño sin porcentaje, denominador y resumen vacío | [test_metrics_service.py](../../backend/tests/decoy/test_metrics_service.py) |
| Token determinista, intacto tras redacción, solo en el señuelo | [test_honeytools.py](../../backend/tests/decoy/test_honeytools.py) |
| Oráculos ignoran los cebos | [test_oracle_invariants.py](../../backend/tests/decoy/test_oracle_invariants.py) |
| 401/403 y proyección pública sin cebos | [test_router.py](../../backend/tests/decoy/test_router.py) |
| Versión nueva junto a la anterior | [test_manifest_versions.py](../../backend/tests/decoy/test_manifest_versions.py) |
| Specs por rol (4 y 6) | [test_model_turn_specs.py](../../backend/tests/victim/test_model_turn_specs.py) |
| Ramas del modelo demo | [test_demo_actions.py](../../backend/tests/llm/test_demo_actions.py) |
| Panel y tarjeta | [DecoyPanel.test.tsx](../../frontend/src/features/operator/DecoyPanel.test.tsx), [RevealCard.test.tsx](../../frontend/src/features/participant/RevealCard.test.tsx) |
