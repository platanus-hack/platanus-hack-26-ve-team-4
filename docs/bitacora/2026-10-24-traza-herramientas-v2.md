---
fecha: 2026-10-24
autor: "@franbastardo"
rama: docs/5-contrato-traza
pr: 31
estado: integrado
dominios: [victim, agent_gateway, oracles, patches, evals, decoy, frontend]
requisitos: [CORE-03]
---

# Contrato v2 de la traza de herramientas

> Registro tardío: el PR #31 se integró a las 13:13 (Caracas) sin esta entrada. Se agrega en el PR de la pulsera en `localStorage`.

## Qué cambió

La traza es lo que la víctima entrega a los oráculos: qué herramienta propuso el modelo, con qué argumentos, qué decidió el gateway y qué cambio de estado quedó. Pasó de un diccionario libre a un esquema tipado y versionado (`schema_version: 2`):

| Cambio | Detalle |
|---|---|
| Esquema compartido | `TraceData` y un modelo por evento, sin campos extra. Escribe `TraceObserver`, lee `oracles/trace_reader.py`. |
| `output` como objeto | Antes viajaba como texto JSON y se volvía a parsear. |
| `effect` | Cambio de estado declarado por el adaptador vía `ToolOutput(text, effect)`: `read` (pedido y dueño), `refund` (importe y saldo antes y después en centavos), `memory_write` o `none`. El modelo no lo ve. Se guarda con la operación idempotente, así que un reintento lo recupera. |
| `tool_failed` | Evento nuevo cuando la herramienta lanza una excepción. Guarda el nombre del error, no su mensaje. |
| Falla cerrada | Un `tool_completed` sin salida u efecto legibles deja el intento `inconclusive`. Antes se ignoraba en silencio. |
| `provenance` | Entra al esquema; la usan las reglas de flujo. |
| Región `ve` | Configuración, herramientas y manifiestos. `tool_denied` ya no repite `attempt_id` ni `policy_version`. |

Los oráculos deciden con `effect` y siguen confirmando contra las filas persistidas: `refunds` por `operation_id` y memoria por `source_run_id`. Los eventos v1 ya guardados se siguen leyendo: su efecto se reconstruye desde la salida.

## Por qué

#5 pedía exponer la traza y acordar su formato con los oráculos de #8. El formato existía pero no estaba escrito: la salida era texto, el cambio de estado («antes y después», como pide #8) no estaba en la traza y una salida ilegible se convertía en `{}`, lo que dejaba de contar una violación en vez de marcar el intento.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/src/agent_zero/victim/trace_schemas.py` | Nuevo: esquema v2 y `ToolEffect`. |
| `backend/src/agent_zero/victim/trace_observer.py` | Escribe cada evento con su modelo; un efecto inválido se guarda como nulo. |
| `backend/src/agent_zero/victim/tool_effects.py` | Nuevo: guarda salida y efecto en `operations.output` con `trace_schema_version`. |
| `backend/src/agent_zero/victim/scenario_tools.py`, `victim/honeytools.py` | Declaran el efecto de cada herramienta; las herramientas cebo, `none`. |
| `backend/src/agent_zero/agent_gateway/` | `ToolOutput`, `effect` en `tool_completed` y emisión de `tool_failed`. |
| `backend/src/agent_zero/oracles/trace_reader.py` | Nuevo: `tool_evidence` para v2 y v1, con `readable`. |
| `backend/src/agent_zero/oracles/*_oracle.py`, `assessment_service.py` | Deciden con `effect`; traza ilegible → `inconclusive`. |
| `backend/src/agent_zero/victim/arena_manifest.py` | `ARENA_VERSION` 2.2.0. |
| `backend/tests/arena/test_tool_trace_contract.py`, `tests/victim/test_trace_reader.py` | Nuevos. |
| `backend/tests/evals/test_round_curve.py` | `digest` de 64 caracteres (commit `03c0369`). |
| `frontend/src/features/arena/` | Tipo y etiqueta de `tool_failed`. |
| `docs/dominio/traza-herramientas.md` | Nuevo: el contrato. Más víctima, oráculos, gateway, eventos, agentes y matriz de pruebas. |

Commits integrados: `546d430` y `03c0369`.

## Cómo se verificó

- Suite completa sobre el código combinado con `main`: 1064 passed y 2 skipped (proveedor real). Ruff, formato y mypy limpios (557 archivos).
- CI del PR #31 en verde: `backend`, `backend-postgres`, `containers` (Docker con smoke) y `frontend`.
- Prueba funcional HTTP sobre Docker con Postgres, en modo `demo`: 50 de 50. Los 40 eventos `tool_*` de la arena salieron con `schema_version: 2` y el efecto correcto por herramienta.
- Actualización real: sobre una base con los manifiestos 2.0.0 en `cl`, el arranque publicó y aprobó `soporte-tienda` 2.2.0 con `ve`, y las herramientas funcionaron.

## Riesgos y efectos en otros frentes

- **Oráculos (@FernandoSiavato):** ahora leen `effect`. Cualquier cambio del contrato se acuerda en `docs/dominio/traza-herramientas.md`.
- **Manifiestos:** `ARENA_VERSION` saltó dos veces el mismo día. La 2.1.0 (herramientas cebo del señuelo, commit `84afc3e`) todavía declaraba `cl`; la 2.2.0 corrige la región. El registro conserva las versiones viejas, así que una base existente publica la nueva al arrancar.
- **Operaciones guardadas antes de la v2:** un reintento devuelve la salida sin efecto, y el intento queda `inconclusive`. Sólo afecta runs en curso durante el despliegue.
- **Recorrido de la flota:** el manifiesto 1.0.0 también usa la región `ve` y conserva su versión. Sobre una base que ya lo publicó con `cl`, sus herramientas se denegarían; se ejecuta contra datos nuevos.
- **CI de `main`:** `backend-postgres` fallaba desde `1f8633e` por `test_round_curve.py`. Se corrigió en este PR.

## Pendiente

- El límite del gateway (`AGENT_ZERO_GATEWAY_RATE_LIMIT_PER_MINUTE`, 60 por defecto) se cuenta por agente: todos los participantes, el Prober, la validación y la evaluación comparten 60 llamadas por minuto. En la prueba funcional, 46 de 90 ejecuciones de la evaluación fueron `rate_limited`.
- El señuelo inventa también los pedidos propios de la sesión desviada; un participante que ya vio su pedido real nota el cambio. Visto en la corrida LIVE del 2026-10-24.
- Cerrar #5 con referencia a este PR.
