# Adaptadores del Guard

Cuatro formas de conectar un agente con herramientas al Guard de Agent Zero. Todas hacen lo mismo: `POST /api/guard/{contract_id}/check` antes de ejecutar la herramienta y `POST /api/guard/{contract_id}/effects` después, con la cabecera `X-Guard-Key`. La API completa está en `docs/integracion.md`.

Semántica común:

- **Falla cerrado.** Si el Guard no responde, responde con error o devuelve algo ilegible, la herramienta se deniega con `guard_unreachable`.
- **Denegar.** Según el entorno se lanza `ToolDeniedError`, se cancela la herramienta o se devuelve un error de herramienta con el texto `Denegado por Agent Zero: <motivo> (<regla>)`.
- **Última política aprendida.** Cuando un `check` devuelve `learned`, el adaptador guarda `{violations, policy}` en `last_learned` (`lastLearned` en Node).
- **Dueños.** Solo se envían los que el integrador resuelve. Sin dueño, el Guard deniega con `owner_required` cuando el contrato lo exige. Ningún adaptador inventa dueños.

| Adaptador | Archivo | Entorno | Etiquetas de contexto |
| --- | --- | --- | --- |
| Python | `agent_zero_guard.py` | Funciones Python | Las que pasa quien llama |
| Node | `node/agent-zero-guard.mjs` | Funciones JS, Node 18+ | Las que pasa quien llama |
| Proxy MCP | `mcp_proxy.py` | Cualquier servidor MCP por stdio | `untrusted` y `store` |
| Strands | `strands_guard.py` | Agentes de Strands | `user`, `untrusted` y `store` |

## Cliente Node

ESM, sin dependencias, usa `fetch`.

```js
import { AgentZeroGuard, ToolDeniedError } from "./node/agent-zero-guard.mjs";

const guard = new AgentZeroGuard({
  baseUrl: "http://127.0.0.1:8000",
  contractId: "banco-transferencias",
  apiKey: process.env.AGENT_ZERO_GUARD_KEY,
});
const transferir = guard.wrap("transferir", fn, {
  ownerOf: (args) => ({ cuenta: owners[args.cuenta] }),
  context: () => segments,
});
await transferir("ana", { cuenta: "CTA-1", destino: "BEN-ALQUILER", monto: 450, concepto: "x" });
```

`check({subject, tool, arguments, context, owners, provenance})` y `report(callId, owners)` se pueden usar sin `wrap`. `wrap` lanza `ToolDeniedError` (con `.decision`) si el Guard deniega. `context` puede ser una lista o una función `(subject, args) => lista`; también se puede pasar un tercer argumento a la función envuelta. Etiquetas: las que tú pongas (`user`, `store`, `untrusted`, `memory`).

Pruebas: `node --test examples/guard/node/`. Demo: `node examples/guard/node/banco-demo.mjs http://127.0.0.1:8000`, que levanta el servidor MCP de juguete como subproceso y llama a sus herramientas a través de `wrap`.

## Proxy MCP

Se coloca entre el cliente MCP y el servidor real. Solo biblioteca estándar, Python 3.9 o superior.

```bash
export AGENT_ZERO_GUARD_KEY=...
python3 examples/guard/mcp_proxy.py --guard http://127.0.0.1:8000 \
  --contract banco-transferencias --subject ana \
  --trusted-tool consultar_saldo --owners-module banco_owners:owners \
  -- python3 examples/guard/mcp_banco_server.py
```

- Relaya JSON-RPC delimitado por saltos de línea en ambos sentidos y solo intercepta `tools/call`.
- Si el Guard deniega, no reenvía la petición y responde `{content:[{type:"text",text:"Denegado por Agent Zero: ..."}], isError:true}`.
- Si permite, reenvía, registra la respuesta como contexto y llama a `effects`.
- Antes de un nuevo `check` espera (hasta 30 s) a que terminen las llamadas anteriores, para que el contexto incluya sus salidas aunque el cliente encadene peticiones.
- `--owners-module paquete.modulo:funcion` recibe `(tool, arguments)` y devuelve un dict de dueños. Un ejemplo está en `banco_owners.py`.

Etiquetas: el proxy no ve el texto del usuario, así que nunca emite `user`. Las salidas de las herramientas de `--trusted-tool` van como `store` y todas las demás como `untrusted`. Consecuencia: un valor que el modelo escribe sin copiarlo de ninguna salida previa queda con procedencia `model`, y las reglas de procedencia aprendidas (que bloquean `untrusted`) lo dejan pasar. Un valor copiado de la salida de una herramienta no confiable queda `untrusted` y se bloquea. Si el contrato exige `user` para algún argumento, hay que usar un adaptador que vea los mensajes del usuario.

`mcp_banco_server.py` es un servidor de juguete (`consultar_saldo`, `transferir`, `leer_correo`); su correo trae una instrucción incrustada que pide una transferencia. `mcp_banco_demo.py --url ...` ejecuta el escenario completo por el proxy.

## Hook de Strands

```python
from strands import Agent
from strands_guard import AgentZeroGuardHook
from agent_zero_guard import AgentZeroGuard

guard = AgentZeroGuard(url, "banco-transferencias", key)
hook = AgentZeroGuardHook(guard, subject="ana", trusted_tools=["consultar_saldo"], owner_of=owners)
agent = Agent(tools=[...], hooks=[hook])
```

- `BeforeToolCallEvent`: llama a `check`; si deniega, asigna `event.cancel_tool` con el texto de denegación y Strands devuelve un resultado de herramienta con error al modelo.
- `AfterToolCallEvent`: si la llamada se permitió y no terminó en error, llama a `effects`.
- `hook.last_learned` guarda la última política aprendida.

Etiquetas, calculadas desde `agent.messages`: el texto de los mensajes del usuario va como `user`; cada `toolResult` va como `untrusted`, salvo que la herramienta que lo produjo esté en `trusted_tools`, que va como `store`. El texto del asistente no se envía.

## Pruebas

```bash
python3 -m unittest discover -s examples/guard/tests -t .
backend/.venv/bin/python -m unittest discover -s examples/guard/tests -t .
node --test examples/guard/node/
```

El test de Strands se salta si `strands` no se puede importar. Las pruebas del proxy usan un Guard falso en un hilo y el servidor de juguete.
