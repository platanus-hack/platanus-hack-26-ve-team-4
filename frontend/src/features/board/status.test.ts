import { describe, expect, it } from "vitest";
import { concealedSession, liveAttempt, liveSession } from "./fixtures";
import { chatStatus, speakerLabel } from "./status";

const orderDenial = {
  tool: "get_order",
  reason: "business_rule_denied",
  validator: "order_belongs_to_session_customer",
};

describe("buena fe del Público", () => {
  it("un Público revelado sin negaciones de validador conversa sin señales de riesgo", () => {
    const audience = liveSession("1", { kind: "audience", alias: "neo" });
    expect(chatStatus(audience, true, true)).toEqual({
      tone: "neutral",
      label: "Conversando",
      detail: "Sin señales de riesgo",
    });
  });

  it("un Público con el intento en curso conversa en su primer mensaje", () => {
    const audience = liveSession("1", {
      kind: "audience",
      alias: "neo",
      attempts: [liveAttempt({ status: "running", outcome: null })],
    });
    expect(chatStatus(audience, true, true)).toMatchObject({
      label: "Conversando",
      detail: "Primer mensaje",
    });
  });

  it("una negación de validador en el Público es una señal de riesgo con su intento", () => {
    const audience = liveSession("1", {
      kind: "audience",
      alias: "neo",
      attempts: [liveAttempt({ outcome: "not_achieved", denials: [orderDenial] })],
    });
    expect(chatStatus(audience, true, true)).toEqual({
      tone: "neutral",
      label: "Señal de riesgo",
      detail: "pedido ajeno · interacción 1",
    });
  });

  it("un límite de uso (rate_limited, sin validador) no es señal de riesgo", () => {
    const audience = liveSession("1", {
      kind: "audience",
      alias: "neo",
      attempts: [
        liveAttempt({
          outcome: "not_achieved",
          denials: [{ tool: "get_order", reason: "rate_limited", validator: null }],
        }),
      ],
    });
    expect(chatStatus(audience, true, true)).toMatchObject({
      label: "Conversando",
      detail: "Sin señales de riesgo",
    });
  });

  it("un pedido mal escrito (order_exists) no es señal de riesgo", () => {
    const audience = liveSession("1", {
      kind: "audience",
      alias: "neo",
      attempts: [
        liveAttempt({
          outcome: "not_achieved",
          denials: [
            { tool: "get_order", reason: "business_rule_denied", validator: "order_exists" },
          ],
        }),
      ],
    });
    expect(chatStatus(audience, true, true)).toMatchObject({
      label: "Conversando",
      detail: "Sin señales de riesgo",
    });
  });

  it("un Público enmascarado conversa igual, aunque su intento traiga un desenlace", () => {
    const hidden = concealedSession("1");
    expect(chatStatus(hidden, true, false)).toEqual({
      tone: "neutral",
      label: "Conversando",
      detail: "Oculto hasta revelar",
    });
    const leaked = concealedSession("1", {
      attempts: [liveAttempt({ id: "att-1", outcome: "confirmed_violation", route: null })],
    });
    expect(chatStatus(leaked, true, false)).toEqual(chatStatus(hidden, true, false));
  });

  it("un Público con una violación confirmada sin parche sigue como filtrado", () => {
    const audience = liveSession("1", {
      kind: "audience",
      alias: "neo",
      attempts: [
        liveAttempt({ outcome: "confirmed_violation", violated_objectives: ["datos internos"] }),
      ],
    });
    expect(chatStatus(audience, true, true)).toMatchObject({
      tone: "leak",
      label: "Se filtró",
      detail: "datos internos · interacción 1",
    });
  });

  it("el rótulo de las burbujas: Participante para el Público, Atacante para el enjambre y el Prober", () => {
    expect(speakerLabel("audience")).toBe("Participante");
    expect(speakerLabel("swarm")).toBe("Atacante");
    expect(speakerLabel("prober")).toBe("Atacante");
  });
});

describe("el enjambre conserva su lenguaje de ataque", () => {
  it("el enjambre con un intento no logrado sigue en Atacando", () => {
    expect(chatStatus(liveSession("1"), true, true)).toEqual({
      tone: "neutral",
      label: "Atacando",
      detail: "Último: no logrado",
    });
  });
});
