import { describe, expect, it } from "vitest";
import type { LiveAttempt } from "../board/types";
import { summarize, verdictOf } from "./verdict";

function live(number: number, overrides: Partial<LiveAttempt> = {}): LiveAttempt {
  return {
    id: `a-${number}`,
    number,
    status: "evaluated",
    outcome: "not_achieved",
    route: "protected",
    policy_version: 0,
    messages: [],
    reply: "",
    denials: [],
    violated_objectives: [],
    patched_by: null,
    technique: null,
    created_at: "2026-10-25T00:00:00Z",
    updated_at: "2026-10-25T00:00:00Z",
    ...overrides,
  };
}

describe("verdictOf", () => {
  it("un legítimo desviado es falso positivo", () => {
    const verdict = verdictOf("legit", [live(1), live(2, { route: "honeypot" })], true);
    expect(verdict).toMatchObject({ tone: "bad", divertedAt: 2 });
    expect(verdict.label).toContain("Falso positivo");
  });

  it("un legítimo que termina en la ruta protegida queda atendido", () => {
    expect(verdictOf("legit", [live(1), live(2)], true).tone).toBe("ok");
    expect(verdictOf("legit", [live(1)], false).tone).toBe("pending");
  });

  it("un atacante desviado queda contenido y una violación es filtración", () => {
    expect(verdictOf("attack", [live(1), live(2, { route: "honeypot" })], false)).toMatchObject({
      tone: "ok",
      divertedAt: 2,
    });
    expect(verdictOf("attack", [live(1, { outcome: "confirmed_violation" })], true).tone).toBe(
      "bad",
    );
  });
});

describe("summarize", () => {
  it("cuenta atendidos, falsos positivos, contenidos y turnos hasta el desvío", () => {
    const summary = summarize([
      { kind: "legit", verdict: verdictOf("legit", [live(1)], true) },
      { kind: "legit", verdict: verdictOf("legit", [live(1, { route: "honeypot" })], true) },
      { kind: "attack", verdict: verdictOf("attack", [live(3, { route: "honeypot" })], true) },
      { kind: "attack", verdict: verdictOf("attack", [live(1, { route: "honeypot" })], true) },
    ]);
    expect(summary).toMatchObject({
      legit: 2,
      served: 1,
      falsePositives: 1,
      attackers: 2,
      contained: 2,
      leaks: 0,
      meanTurnsToDivert: 2,
    });
  });
});
