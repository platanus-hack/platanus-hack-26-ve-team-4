import { describe, expect, it } from "vitest";
import { familyOf, signalLabel } from "./labels";
import type { MonitorAttempt } from "./types";

const base = {
  route: "protected",
  outcome: "not_achieved",
  family: null,
  signals: [],
} as unknown as MonitorAttempt;

describe("familyOf con señales de intención", () => {
  it("sin señales sigue diciendo que no hay objetivo adversario", () => {
    expect(familyOf(base)).toBe("Sin objetivo adversario");
  });

  it("con una señal y sin hallazgos nombra la señal, no un ataque", () => {
    expect(familyOf({ ...base, signals: ["data_request"] })).toBe(
      "Señal: Pidió datos de pedidos o de otros",
    );
  });

  it("una familia del analizador o el señuelo tienen prioridad sobre la señal", () => {
    expect(familyOf({ ...base, family: "direct_injection", signals: ["off_scope"] })).toBe(
      "Inyección directa",
    );
    expect(familyOf({ ...base, route: "honeypot", signals: ["off_scope"] })).toBe(
      "Sesión desviada",
    );
  });

  it("una señal desconocida se muestra tal cual", () => {
    expect(signalLabel("otra")).toBe("otra");
  });
});
