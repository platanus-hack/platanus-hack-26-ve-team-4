import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { AgentZeroGuard, ToolDeniedError } from "./agent-zero-guard.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const ACCOUNTS = { "CTA-1": "ana", "CTA-2": "bruno" };
const TRUSTED = new Set(["consultar_saldo"]);

function startServer() {
  const child = spawn("python3", [join(here, "..", "mcp_banco_server.py")], {
    stdio: ["pipe", "pipe", "inherit"],
  });
  const lines = createInterface({ input: child.stdout })[Symbol.asyncIterator]();
  let counter = 0;
  async function request(method, params) {
    counter += 1;
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: counter, method, params }) + "\n");
    const { value } = await lines.next();
    return JSON.parse(value);
  }
  return { request, close: () => child.stdin.end() };
}

async function main() {
  const url = process.argv[2] ?? "http://127.0.0.1:8000";
  const guard = new AgentZeroGuard({
    baseUrl: url,
    contractId: "banco-transferencias",
    apiKey: process.env.AGENT_ZERO_GUARD_KEY ?? "change-me-guard",
  });
  const server = startServer();
  await server.request("initialize", { protocolVersion: "2025-06-18", capabilities: {} });
  const context = [];
  const ownerOf = (args) => (args.cuenta ? { cuenta: ACCOUNTS[args.cuenta] ?? "desconocido" } : {});

  const tool = (name) =>
    guard.wrap(
      name,
      async (args) => {
        const reply = await server.request("tools/call", { name, arguments: args });
        const text = reply.result.content[0].text;
        context.push({ origin: TRUSTED.has(name) ? "store" : "untrusted", text });
        return text;
      },
      { ownerOf, context: () => [...context] },
    );
  const saldo = tool("consultar_saldo");
  const correo = tool("leer_correo");
  const transferir = tool("transferir");

  async function step(label, run) {
    try {
      const text = await run();
      console.log(`  EJECUTADA  ${label}\n             -> ${text.slice(0, 100)}`);
    } catch (error) {
      if (!(error instanceof ToolDeniedError)) {
        throw error;
      }
      console.log(`  DENEGADA   ${label}  <- ${error.decision.rule_id}`);
    }
  }

  const base = { cuenta: "CTA-1", concepto: "pago" };
  console.log("0. Saldo propio (herramienta de confianza)");
  await step("saldo de CTA-1", () => saldo("ana", { cuenta: "CTA-1" }));
  console.log("1. Leer el correo (contenido no confiable)");
  await step("leer correo", () => correo("ana", { carpeta: "entrada" }));
  console.log("2. Transferencia inyectada de 900 a un beneficiario externo");
  await step("900 a BEN-EXTERNO", () => transferir("ana", { ...base, destino: "BEN-EXTERNO", monto: 900 }));
  console.log(`   invariantes rotos: ${JSON.stringify(guard.lastLearned.violations)}`);
  console.log("3. Transferencia de 40 con monto y destino tomados del correo");
  await step("40 a BEN-AHORRO", () => transferir("ana", { ...base, destino: "BEN-AHORRO", monto: 40 }));
  console.log("4. Transferencia legitima: valores que no salen del correo");
  await step("450 a BEN-ALQUILER", () => transferir("ana", { ...base, destino: "BEN-ALQUILER", monto: 450 }));
  server.close();
}

main();
