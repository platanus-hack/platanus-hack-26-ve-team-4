export class ToolDeniedError extends Error {
  constructor(decision) {
    super(decision.reason || decision.rule_id || "denegado");
    this.name = "ToolDeniedError";
    this.decision = decision;
  }
}

const UNREACHABLE = {
  allowed: false,
  rule_id: "guard_unreachable",
  reason: "Guard caído.",
};

export class AgentZeroGuard {
  constructor({ baseUrl, contractId, apiKey, timeout = 5000, fetch: fetchImpl } = {}) {
    this.baseUrl = String(baseUrl).replace(/\/+$/, "");
    this.contractId = contractId;
    this.apiKey = apiKey;
    this.timeout = timeout;
    this.fetch = fetchImpl || globalThis.fetch;
    this.verdicts = [];
    this.lastLearned = {};
  }

  async #post(path, body) {
    const response = await this.fetch(`${this.baseUrl}/api/guard/${this.contractId}/${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-guard-key": this.apiKey },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(this.timeout),
    });
    if (!response.ok) {
      throw new Error(`Guard respondió ${response.status}`);
    }
    return response.json();
  }

  async check({ subject, tool, arguments: args = {}, context = [], owners = {}, provenance }) {
    const body = { subject, tool, arguments: args, context, owners };
    if (provenance) {
      body.provenance = provenance;
    }
    try {
      const decision = await this.#post("check", body);
      if (decision.learned) {
        this.lastLearned = {
          violations: decision.learned.report?.violated ?? [],
          policy: decision.learned,
        };
      }
      return decision;
    } catch {
      return { ...UNREACHABLE };
    }
  }

  async report(callId, owners = {}) {
    const verdict = await this.#post("effects", { call_id: callId, owners });
    this.verdicts.push(verdict);
    return verdict;
  }

  wrap(tool, fn, { ownerOf, context } = {}) {
    return async (subject, args = {}, callContext) => {
      const owners = ownerOf ? await ownerOf(args) : {};
      const segments =
        callContext ?? (typeof context === "function" ? await context(subject, args) : context ?? []);
      const decision = await this.check({
        subject,
        tool,
        arguments: args,
        context: segments,
        owners,
      });
      if (!decision.allowed) {
        throw new ToolDeniedError(decision);
      }
      const result = await fn(args);
      await this.report(decision.call_id, owners);
      return result;
    };
  }
}
