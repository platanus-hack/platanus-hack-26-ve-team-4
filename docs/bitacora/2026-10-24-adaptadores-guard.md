---
fecha: 2026-10-24
autor: "@carlos"
rama: worktree-agent-ac5653937505c4034
pr: pendiente
estado: en revisión
dominios: [guard, integracion]
requisitos: []
---

# Adaptadores del Guard para Node, MCP y Strands

## Qué cambió

Tres adaptadores nuevos con la misma semántica que el cliente Python (falla cerrado, denegar, guardar la última política aprendida):

- Cliente Node `AgentZeroGuard` con `check`, `report`, `wrap` y `ToolDeniedError`.
- Proxy MCP por stdio que intercepta `tools/call`, con un servidor MCP de juguete del banco.
- Hook de Strands (`AgentZeroGuardHook`) sobre `BeforeToolCallEvent` y `AfterToolCallEvent`.

Más pruebas, dos demos del escenario del banco y un README de adaptadores.

## Por qué

`docs/integracion.md` decía que solo existía el envoltorio de Python. Los demás entornos eran "el mismo contrato de dos llamadas" sin código.

## Archivos

- `examples/guard/node/agent-zero-guard.mjs`, `agent-zero-guard.test.mjs`, `banco-demo.mjs`
- `examples/guard/mcp_proxy.py`, `mcp_banco_server.py`, `mcp_banco_demo.py`, `banco_owners.py`
- `examples/guard/strands_guard.py`
- `examples/guard/tests/` (un test por fuente y un Guard falso en `fake_guard.py`)
- `examples/guard/README.md`

## Cómo se verificó

- `python3 -m unittest discover -s examples/guard/tests -t .` con Python 3.9: 11 pruebas, 4 saltadas (Strands no instalado).
- Lo mismo con `backend/.venv/bin/python` (3.12): 11 pruebas, 0 saltadas.
- `node --test examples/guard/node/agent-zero-guard.test.mjs` con Node 24: 6 pruebas.
- Backend en modo demo (puerto 8021, directorio de datos temporal, clave local por defecto) con el contrato `banco-transferencias`:
  - Por el proxy MCP: el correo se lee, la transferencia de 900 se deniega por `invariant:tope-por-transferencia`, la de 40 con monto y destino del correo se deniega por la regla aprendida de procedencia y la de 450 a `BEN-ALQUILER` se ejecuta.
  - Con el cliente Node: mismo resultado.
- En el proxy, un valor que el modelo escribe sin copiarlo de ninguna salida queda con procedencia `model` y las reglas aprendidas (que bloquean `untrusted`) lo permiten. No hay texto de usuario en el proxy, así que nunca se emite `user`.

## Riesgos y efectos en otros frentes

- No toca `backend/src` ni los documentos de dominio.
- El proxy espera hasta 30 s a que terminen las llamadas anteriores antes de cada `check`; con un servidor que no responde, la siguiente llamada se retrasa ese tiempo.
- `mcp_proxy.py` supera ligeramente las 200 líneas por contener el cliente HTTP, para poder copiarlo como un solo archivo.
- Un fallo de `effects` en el hook de Strands se propaga igual que en el cliente Python; no se captura.

## Pendiente

Reemplazar la tabla y la frase final del paso 6 de `docs/integracion.md` por:

```markdown
| Entorno | Dónde va el `check` | Adaptador |
| --- | --- | --- |
| Función Python | Envoltorio de la herramienta | [`agent_zero_guard.py`](../examples/guard/agent_zero_guard.py) |
| Función Node | Envoltorio de la herramienta | [`node/agent-zero-guard.mjs`](../examples/guard/node/agent-zero-guard.mjs) |
| MCP | Proxy entre el cliente y el servidor MCP, en `tools/call` | [`mcp_proxy.py`](../examples/guard/mcp_proxy.py) |
| Strands | Hook `BeforeToolCallEvent` / `AfterToolCallEvent` | [`strands_guard.py`](../examples/guard/strands_guard.py) |
| LangChain, OpenAI Agents | Callback o hook previo a la herramienta | Mismo patrón; sin adaptador todavía |
| Gateway HTTP propio | Middleware sobre los endpoints que el agente invoca | Mismo patrón; sin adaptador todavía |

Los cuatro adaptadores comparten la semántica: fallan cerrado, deniegan con un error de herramienta y guardan la última política aprendida. Su uso y las etiquetas de contexto de cada uno están en [`examples/guard/README.md`](../examples/guard/README.md).
```
