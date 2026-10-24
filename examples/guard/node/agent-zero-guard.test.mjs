import assert from "node:assert/strict";
import test from "node:test";

import { AgentZeroGuard, ToolDeniedError } from "./agent-zero-guard.mjs";

function fakeFetch(handlers) {
  const calls = [];
  const impl = async (url, init) => {
    const path = new URL(url).pathname.split("/").pop();
    const body = JSON.parse(init.body);
    calls.push({ path, body, headers: init.headers, url });
    const result = handlers[path](body);
    if (result instanceof Error) {
      throw result;
    }
    return {
      ok: result.status === undefined,
      status: result.status ?? 200,
      json: async () => result.json ?? result,
    };
  };
  impl.calls = calls;
  return impl;
}

function build(handlers) {
  const fetch = fakeFetch(handlers);
  const guard = new AgentZeroGuard({
    baseUrl: "http://guard.test/",
    contractId: "banco",
    apiKey: "k",
    fetch,
  });
  return { guard, fetch };
}

test("check envía la clave, el cuerpo y devuelve la decisión", async () => {
  const { guard, fetch } = build({ check: () => ({ allowed: true, call_id: "gc-1" }) });
  const decision = await guard.check({
    subject: "ana",
    tool: "transferir",
    arguments: { monto: 1 },
    context: [{ origin: "user", text: "x" }],
  });
  assert.equal(decision.allowed, true);
  const call = fetch.calls[0];
  assert.equal(call.url, "http://guard.test/api/guard/banco/check");
  assert.equal(call.headers["x-guard-key"], "k");
  assert.deepEqual(call.body.owners, {});
  assert.equal(call.body.subject, "ana");
});

test("falla cerrado si el Guard no responde", async () => {
  const { guard } = build({ check: () => new TypeError("fetch failed") });
  const decision = await guard.check({ subject: "ana", tool: "t" });
  assert.equal(decision.allowed, false);
  assert.equal(decision.rule_id, "guard_unreachable");
});

test("falla cerrado ante un estado HTTP de error", async () => {
  const { guard } = build({ check: () => ({ status: 401, json: {} }) });
  const decision = await guard.check({ subject: "ana", tool: "t" });
  assert.equal(decision.rule_id, "guard_unreachable");
});

test("wrap ejecuta y reporta efectos cuando se permite", async () => {
  const { guard, fetch } = build({
    check: () => ({ allowed: true, call_id: "gc-9" }),
    effects: () => ({ call_id: "gc-9", violations: [] }),
  });
  const seen = [];
  const tool = guard.wrap("transferir", async (args) => seen.push(args), {
    ownerOf: (args) => ({ cuenta: args.cuenta === "CTA-1" ? "ana" : "otro" }),
    context: [{ origin: "user", text: "paga" }],
  });
  await tool("ana", { cuenta: "CTA-1", monto: 5 });
  assert.deepEqual(seen, [{ cuenta: "CTA-1", monto: 5 }]);
  assert.deepEqual(fetch.calls[0].body.owners, { cuenta: "ana" });
  assert.deepEqual(fetch.calls[0].body.context, [{ origin: "user", text: "paga" }]);
  assert.equal(fetch.calls[1].path, "effects");
  assert.deepEqual(fetch.calls[1].body, { call_id: "gc-9", owners: { cuenta: "ana" } });
  assert.equal(guard.verdicts.length, 1);
});

test("wrap lanza ToolDeniedError, no ejecuta y guarda la política aprendida", async () => {
  const learned = { version: 1, report: { violated: ["tope"] }, rules: [] };
  const { guard, fetch } = build({
    check: () => ({ allowed: false, rule_id: "invariant:tope", reason: "tope", learned }),
  });
  let ran = false;
  const tool = guard.wrap("transferir", async () => {
    ran = true;
  });
  await assert.rejects(
    () => tool("ana", { monto: 900 }),
    (error) => error instanceof ToolDeniedError && error.decision.rule_id === "invariant:tope",
  );
  assert.equal(ran, false);
  assert.equal(fetch.calls.length, 1);
  assert.deepEqual(guard.lastLearned.violations, ["tope"]);
  assert.equal(guard.lastLearned.policy.version, 1);
});

test("wrap acepta contexto dinámico por llamada", async () => {
  const { guard, fetch } = build({
    check: () => ({ allowed: false, rule_id: "x" }),
  });
  const tool = guard.wrap("t", async () => 1, {
    context: (subject) => [{ origin: "user", text: subject }],
  });
  await assert.rejects(() => tool("ana", {}), ToolDeniedError);
  assert.deepEqual(fetch.calls[0].body.context, [{ origin: "user", text: "ana" }]);
});
