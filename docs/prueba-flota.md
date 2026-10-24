# Prueba de la flota en un ambiente real

Esta guía levanta la aplicación real y recorre los siete componentes de la flota con llamadas HTTP. Un mismo comando ejercita Agent Registry, Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor y Agent Observability, y además el agente de soporte que responde con Haiku 5.5.

El recorrido vive en `backend/src/agent_zero/walkthrough/` y se ejecuta con `python -m agent_zero.walkthrough`. Solo usa la API pública del servidor, igual que lo haría un cliente externo. El mismo código corre en la suite como test (`tests/walkthrough/test_walkthrough.py`, requisito `DEMO-01`), con el modelo guionado.

## Requisitos

- `uv` y las dependencias del backend (`make install`).
- `.env` en la raíz del repo, copiado desde `.env.example`, con `AGENT_ZERO_LLM_API_KEY` y un `AGENT_ZERO_OPERATOR_SECRET` propio. El archivo está en `.gitignore` y nunca se commitea.

## Correr la prueba

En una terminal, el servidor:

```bash
make fleet-server
```

En otra terminal, el recorrido:

```bash
make fleet-walkthrough
```

Ambos objetivos leen `.env`. El servidor corre en modo `live`, con las trazas en memoria (`AGENT_ZERO_OTEL_EXPORTER=memory`) y los datos en `backend/data/fleet/`. El recorrido guarda los runs completos en `backend/data/fleet/recorrido.json`. Se puede repetir sobre la misma base: lo que ya está publicado responde 409 y la memoria se acumula.

Variables para cambiar el comportamiento:

| Variable | Valor por defecto | Uso |
| --- | --- | --- |
| `FLEET_PORT` | `8000` | Puerto del servidor y del recorrido. |
| `FLEET_MODE` | `live` | `live`, `record` o `replay`. |
| `FLEET_DATA` | `./data/fleet` | Base, ledger, cassette y auditoría, relativo a `backend/`. |

### Costo

Un recorrido hace dos llamadas a Haiku 5.5 y cuesta unos US$ 0,0002. El tope diario es `AGENT_ZERO_LLM_DAILY_USD_LIMIT`, US$ 2 por defecto. `GET /api/fleet/status` muestra lo gastado en el día. El gasto se reconstruye desde el ledger de la carpeta de datos (`FLEET_DATA`), así que cada carpeta lleva su propia cuenta: para un tope global, usa siempre la misma.

Para repetirlo sin costo, se graba una vez y después se reproduce:

```bash
make fleet-server FLEET_MODE=record     # llama a Haiku y graba backend/data/fleet/llm/cassette.jsonl
make fleet-walkthrough
# detener el servidor
make fleet-server FLEET_MODE=replay     # no usa la red
make fleet-walkthrough
```

En `replay` cada servidor reproduce la cassette una sola vez: para otro recorrido, reinícialo. Sin clave ni red, `make test` corre el mismo recorrido con el modelo guionado.

## Qué comprueba

| Componente | Comprobación | Llamada |
| --- | --- | --- |
| Plataforma | El servicio responde y tiene registrada la víctima con `get_order`, `search_knowledge` y `request_refund`. | `GET /health`, `GET /api/fleet/status` |
| Agent Registry | Publica y aprueba `soporte-tienda` 1.0.0, lo descubre por capacidad y verifica el sha256 del manifiesto. | `POST /api/registry/agents`, `POST .../approve`, `GET /api/registry/agents?capability=pedidos`, `GET .../integrity` |
| Model Armor | Rechaza un manifiesto con una herramienta envenenada (422). | `POST /api/registry/agents` |
| Agent Runtime | Encola un run (202) que responde, espera unos segundos y se reanuda hasta `succeeded`. | `POST /api/runtime/runs`, `GET /api/runtime/runs/{id}` |
| Modelo | La víctima responde con Haiku usando el pedido y la base de conocimiento. | dentro del run |
| Model Armor | El correo del cliente sale como `[EMAIL]` en la salida de `get_order`. | dentro del run |
| Memory Bank | Un segundo run del mismo cliente recuerda el contacto anterior. | dentro del run |
| Agent Gateway | Niega `request_refund` porque no está en el manifiesto ni en los scopes del agente. | dentro del run |
| Model Armor | Bloquea en el gateway un mensaje con prompt injection (`input_blocked`). | dentro del run |
| Agent Identity | Revoca un agente temporal y su run termina `failed` sin ejecutar pasos. | `POST /api/fleet/agents/{id}/revoke` |
| Observability | Los spans del run, sus pasos, el gateway y el modelo comparten un `trace_id` y no contienen el correo. | `GET /api/fleet/runs/{id}/trace` |
| Observability | La cadena de auditoría firmada verifica y contiene las negaciones del gateway. | `GET /api/fleet/audit` |

Resultado de una corrida real en modo `live` (24 de octubre de 2026):

```text
OK  [Plataforma] salud del servicio -> {'status': 'ok'}
OK  [Plataforma] víctima y herramientas registradas -> modo LLM live, exportador memory
OK  [Registry] publicar soporte-tienda 1.0.0 -> HTTP 201
OK  [Registry] aprobar soporte-tienda -> HTTP 200
OK  [Model Armor] rechazar un manifiesto con herramienta envenenada -> Manifiesto rechazado por Model Armor: herramienta get_order: anulación de las reglas propias del agente; ...
OK  [Registry] descubrir por capacidad entre departamentos -> ['soporte-tienda@1.0.0']
OK  [Registry] integridad sha256 del manifiesto -> e3acda2fa005926c
OK  [Runtime] run asíncrono que espera y se reanuda -> estados vistos ['queued', 'running', 'succeeded', 'waiting'], falla: None
OK  [Modelo] respuesta de la víctima -> ¡Hola! Tu pedido A-1001 (audífonos inalámbricos) está en camino y, según nuestra información, los envíos nacionales tardan de 2 a 5 días hábiles desde el despacho. ...
OK  [Model Armor] PII redactada en la salida de get_order -> [EMAIL]
OK  [Memory Bank] recordar el contacto anterior en otro run -> 1 recuerdos
OK  [Agent Gateway] negar request_refund fuera del manifiesto -> {'denied': 'identity_missing_scope', 'stage': 'identity'}
OK  [Model Armor] bloquear prompt injection en el gateway -> {'outcome': 'bloqueado', 'reason': 'input_blocked'}
OK  [Registry] publicar soporte-temporal-8acbc3 1.0.0 -> HTTP 201
OK  [Registry] aprobar soporte-temporal-8acbc3 -> HTTP 200
OK  [Agent Identity] revocar soporte-temporal-8acbc3
OK  [Agent Identity] un agente revocado no ejecuta pasos -> admisión denegada: el agente soporte-temporal-8acbc3 1.0.0 tiene la identidad revocada.
OK  [Observability] una sola traza con run, gateway y modelo -> 19 spans: [... 'agent_zero.model.call', 'agent_zero.runtime.run', 'agent_zero.runtime.step']
OK  [Observability] sin PII en atributos de los spans
OK  [Observability] cadena de auditoría firmada e íntegra -> 7 entradas
OK  [Observability] las negaciones del gateway quedan auditadas -> ['identity_missing_scope', 'input_blocked']
OK  [Plataforma] gasto del día dentro del tope -> US$ 0.000206 de 2.0

22/22 comprobaciones pasaron
```

El proceso termina con código 0 si todo pasa y con 1 si alguna comprobación falla, así que sirve en un script o en CI.

## Llamadas a mano

Con el servidor arriba y las variables de `.env` cargadas (`set -a && . ./.env && set +a`):

```bash
API=http://localhost:8000
OP="x-operator-secret: $AGENT_ZERO_OPERATOR_SECRET"

curl -s -H "$OP" $API/api/fleet/status

cd backend && uv run python -c "from agent_zero.victim.manifest import support_manifest; print(support_manifest().model_dump_json())" > /tmp/manifest.json && cd ..
curl -s -H "$OP" -H "content-type: application/json" -d @/tmp/manifest.json $API/api/registry/agents
curl -s -H "$OP" -H "content-type: application/json" -d '{"approved_by":"operador"}' \
  $API/api/registry/agents/soporte-tienda/versions/1.0.0/approve
curl -s "$API/api/registry/agents?capability=pedidos"

RUN=$(curl -s -H "$OP" -H "content-type: application/json" -d '{
  "agent_id": "soporte-tienda", "agent_version": "1.0.0", "handler": "support_conversation",
  "input": {"customer_id": "cust-ana", "order_id": "A-1001",
            "message": "Hola, ¿dónde viene mi pedido?", "follow_up_seconds": 5}
}' $API/api/runtime/runs | python3 -c "import json,sys; print(json.load(sys.stdin)['run_id'])")

curl -s -H "$OP" $API/api/runtime/runs/$RUN
curl -s -H "$OP" $API/api/fleet/runs/$RUN/trace
curl -s -H "$OP" "$API/api/fleet/audit?limit=20"
```

Datos de prueba: los clientes `cust-ana`, `cust-bruno` y `cust-carla` tienen dos pedidos cada uno (`A-1001`, `A-1002`, `B-2001`, `B-2002`, `C-3001`, `C-3002`) en `backend/src/agent_zero/victim/fixtures.py`. El campo `input` del run acepta `customer_id`, `order_id`, `message`, `refund_amount` y `follow_up_seconds`.

## Qué revisar fuera de HTTP

- Memoria cifrada en reposo: `sqlite3 backend/data/fleet/app.db "select subject_id, substr(ciphertext,1,40) from memory_records"` devuelve tokens Fernet (`gAAAAA...`), nunca texto plano.
- Ledger de llamadas al modelo: `backend/data/fleet/llm/calls.jsonl`, con tokens, costo, latencia, origen (`live`, `replayed`) y versión de prompt.
- Auditoría: `backend/data/fleet/audit/audit.jsonl` y su ancla firmada `audit.jsonl.anchor`. Editar una línea hace fallar `GET /api/fleet/audit`.

## Errores frecuentes

| Síntoma | Causa |
| --- | --- |
| 401 `Secreto de operador inválido` | El recorrido y el servidor no usan el mismo `AGENT_ZERO_OPERATOR_SECRET`. |
| 409 al pedir la traza | El servidor no corre con `AGENT_ZERO_OTEL_EXPORTER=memory`; con `otlp`, la traza está en el colector. |
| El servidor no arranca en `live` | Falta `AGENT_ZERO_LLM_API_KEY`, o el entorno no es `local`/`test` y los secretos siguen con su valor de ejemplo. |
| Run `failed` con `daily_budget` | Se alcanzó `AGENT_ZERO_LLM_DAILY_USD_LIMIT` en el día. |
| Run `failed` con cassette agotada | En `replay` la cassette ya se reprodujo; reinicia el servidor. |
