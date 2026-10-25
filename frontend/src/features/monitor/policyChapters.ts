import type { ReplayGraph } from "../arena/replay/types";
import type { Policy } from "../operator/api";
import type { MonitorAttempt } from "./types";

export interface RuleText {
  code: string;
  rule: string;
  gap: string;
}

export interface Chapter {
  version: number;
  status: string;
  rules: RuleText[];
  inherited: RuleText[];
  reason: string;
  attack: string | null;
  effects: { label: string; blocked: boolean }[];
  adversarial: { passed: number; total: number };
  legitimate: { passed: number; total: number };
  learnedSeconds: number | null;
  rationale: string | null;
}

const RULES: Record<string, Omit<RuleText, "code">> = {
  order_belongs_to_session_customer: {
    rule: "Solo se consultan los pedidos del cliente que está escribiendo.",
    gap: "Nada impedía que el agente leyera el pedido de otro cliente.",
  },
  refund_within_limit: {
    rule: "Reembolsos de hasta 20 USD, solo de pedidos propios y sin superar su total.",
    gap: "Nada impedía reembolsar más de 20 USD o el pedido de otra persona.",
  },
  memory_key_allowlist: {
    rule: "La memoria solo guarda preferencias (idioma, nombre), nunca permisos.",
    gap: "Nada impedía guardar en memoria un permiso falso y usarlo después.",
  },
  require_provenance: {
    rule: "El agente no actúa con instrucciones de un documento o resultado no verificado.",
    gap: "Nada impedía que un texto recuperado le ordenara una acción al agente.",
  },
};

export function ruleText(code: string): RuleText {
  const known = RULES[code];
  if (known) return { code, ...known };
  if (code.startsWith("flow:"))
    return {
      code,
      rule: "Regla de flujo: limita qué acción puede seguir a qué dato.",
      gap: "Nada impedía encadenar un dato no confiable con una acción sensible.",
    };
  return { code, rule: code.replaceAll("_", " "), gap: "Faltaba este control." };
}

function effects(before?: ReplayGraph, after?: ReplayGraph) {
  const blocked = new Set(
    (after?.nodes ?? []).filter((node) => node.state === "prevented").map((node) => node.effect),
  );
  return (before?.nodes ?? [])
    .filter((node) => node.kind === "effect" && node.state === "effect")
    .map((node) => ({ label: node.label, blocked: blocked.has(node.effect) }));
}

function count(cases: { passed: boolean; adversarial?: boolean }[], adversarial: boolean) {
  const scoped = cases.filter((item) => Boolean(item.adversarial) === adversarial);
  return { passed: scoped.filter((item) => item.passed).length, total: scoped.length };
}

function learned(policy: Policy, attack: MonitorAttempt | undefined): number | null {
  if (!attack || !policy.activated_at) return null;
  const seconds = (Date.parse(policy.activated_at) - Date.parse(attack.updated_at)) / 1000;
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

function codes(policy: Policy | undefined): string[] {
  if (!policy) return [];
  const all = [...policy.rules, ...(policy.flow_rules ?? []).map((flow) => `flow:${flow.rule_id}`)];
  return all.filter((code, index) => all.indexOf(code) === index);
}

export function policyStory(policies: Policy[], attempts: MonitorAttempt[]): Chapter[] {
  const byId = new Map(attempts.map((attempt) => [attempt.id, attempt]));
  const byVersion = new Map(policies.map((policy) => [policy.version, policy]));
  return [...policies]
    .sort((a, b) => a.version - b.version)
    .map((policy) => {
      const parent = new Set(codes(byVersion.get(policy.parent_version ?? -1)));
      const validation = policy.validation ?? {};
      const evidence = (validation.evidence_attempt_ids ?? [])
        .map((id) => byId.get(id))
        .find(Boolean);
      const cases = validation.cases ?? [];
      return {
        version: policy.version,
        status: policy.status,
        rules: codes(policy)
          .filter((code) => !parent.has(code))
          .map(ruleText),
        inherited: codes(policy)
          .filter((code) => parent.has(code))
          .map(ruleText),
        reason: policy.reason,
        attack: evidence?.messages.join(" · ") ?? null,
        effects: effects(validation.replay?.before.graph, validation.replay?.after.graph),
        adversarial: count(cases, true),
        legitimate: count(cases, false),
        learnedSeconds: learned(policy, evidence),
        rationale: policy.analysis?.explanation?.rationale ?? null,
      };
    });
}
