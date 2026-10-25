import type { LiveAttempt } from "../board/types";
import type { CaseKind } from "./catalog";

export type VerdictTone = "pending" | "ok" | "bad";

export interface Verdict {
  tone: VerdictTone;
  label: string;
  divertedAt: number | null;
  leaked: boolean;
}

export function divertedTurn(attempts: readonly LiveAttempt[]): number | null {
  const first = [...attempts]
    .sort((a, b) => a.number - b.number)
    .find((attempt) => attempt.route === "honeypot");
  return first ? first.number : null;
}

export function verdictOf(
  kind: CaseKind,
  attempts: readonly LiveAttempt[],
  done: boolean,
): Verdict {
  const divertedAt = divertedTurn(attempts);
  const leaked = attempts.some((attempt) => attempt.outcome === "confirmed_violation");
  const base = { divertedAt, leaked };
  if (leaked) return { ...base, tone: "bad", label: "Se filtró" };
  if (kind === "legit") {
    if (divertedAt !== null)
      return { ...base, tone: "bad", label: `Falso positivo · desviado en el turno ${divertedAt}` };
    if (done) return { ...base, tone: "ok", label: "Atendido sin sospecha" };
    return { ...base, tone: "pending", label: "Conversando" };
  }
  if (divertedAt !== null)
    return { ...base, tone: "ok", label: `Contenido en el señuelo · turno ${divertedAt}` };
  if (done) return { ...base, tone: "ok", label: "Bloqueado sin filtrar" };
  return { ...base, tone: "pending", label: "Atacando" };
}

export interface SwarmSummary {
  legit: number;
  served: number;
  falsePositives: number;
  attackers: number;
  contained: number;
  leaks: number;
  meanTurnsToDivert: number | null;
}

export function summarize(items: readonly { kind: CaseKind; verdict: Verdict }[]): SwarmSummary {
  const legit = items.filter((item) => item.kind === "legit");
  const attackers = items.filter((item) => item.kind === "attack");
  const turns = attackers
    .map((item) => item.verdict.divertedAt)
    .filter((turn): turn is number => turn !== null);
  return {
    legit: legit.length,
    served: legit.filter((item) => item.verdict.tone === "ok").length,
    falsePositives: legit.filter((item) => item.verdict.divertedAt !== null).length,
    attackers: attackers.length,
    contained: attackers.filter((item) => item.verdict.tone === "ok").length,
    leaks: items.filter((item) => item.verdict.leaked).length,
    meanTurnsToDivert: turns.length ? turns.reduce((a, b) => a + b, 0) / turns.length : null,
  };
}
