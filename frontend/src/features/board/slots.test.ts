import { describe, expect, it } from "vitest";
import { audienceSession, liveAttempt, liveSession, NOW } from "./fixtures";
import { assignSlots, focusIndex, frames, togglePin, windowOf } from "./slots";
import { ago, carouselItem, chatStatus } from "./status";
import type { LiveSession } from "./types";
import { stageScale } from "./useStageScale";

describe("lugares del carrusel", () => {
  const sessions = (...ids: string[]) =>
    new Map(ids.map((id) => [id, liveSession(id)] as [string, LiveSession]));

  it("conserva el lugar de cada sesión y completa los huecos", () => {
    expect(assignSlots(["2", "1"], sessions("1", "2", "3"), new Set(), 8)).toEqual(["2", "1", "3"]);
  });

  it("reemplaza el lugar más antiguo sin fijar cuando todos están llenos", () => {
    const known = sessions("1", "2", "3");
    known.set("9", liveSession("9", { last_activity: "2026-10-24T15:00:59+00:00" }));

    expect(assignSlots(["1", "2", "3"], known, new Set(), 3)).toEqual(["9", "2", "3"]);
    expect(assignSlots(["1", "2", "3"], known, new Set(["1"]), 3)).toEqual(["1", "9", "3"]);
    expect(assignSlots(["1", "2", "3"], known, new Set(["1", "2", "3"]), 3)).toEqual([
      "1",
      "2",
      "3",
    ]);
  });
});

describe("fijar", () => {
  it("fija como máximo 2 y avisa cuál se suelta", () => {
    let state = togglePin([], "a");
    state = togglePin(state.order, "b");
    expect(state).toEqual({ order: ["a", "b"], released: null });
    state = togglePin(state.order, "c");
    expect(state).toEqual({ order: ["b", "c"], released: "a" });
    expect(togglePin(state.order, "b")).toEqual({ order: ["c"], released: null });
  });

  it("deja los fijados a la izquierda y el resto en la ventana", () => {
    const ids = ["1", "2", "3", "4", "5"];
    const win = windowOf(ids, ["4"], 1);
    expect(win.visible).toEqual(["4", "2", "3"]);
    expect(win.order).toEqual(["4", "1", "2", "3", "5"]);
    expect(win.maxIndex).toBe(2);
    expect(windowOf(ids, [], 99).start).toBe(2);
  });

  it("centra un chat que no se ve y no mueve uno que ya se ve", () => {
    const free = ["1", "2", "3", "4", "5", "6"];
    expect(focusIndex(free, "6", 0, 3)).toBe(4);
    expect(focusIndex(free, "2", 0, 3)).toBe(0);
  });

  it("dibuja un marco por tramo contiguo visible sobre la grilla de 153 px", () => {
    expect(frames(["1", "2", "3", "4"], ["1", "2", "3"])).toEqual([{ left: -4, width: 483 }]);
    expect(frames(["5", "1", "2", "3"], ["5", "2"])).toHaveLength(2);
  });
});

describe("estado del chat", () => {
  it("Bloqueado solo con prevented o con un parche vigente", () => {
    const blocked = liveSession("1", {
      prevented_n: 2,
      attempts: [liveAttempt({ outcome: "prevented" })],
    });
    expect(chatStatus(blocked, true, false)).toEqual({
      tone: "blocked",
      label: "Bloqueado",
      detail: "2 frenados",
    });
    const failed = liveSession("1", { attempts: [liveAttempt({ outcome: "not_achieved" })] });
    expect(chatStatus(failed, true, false)).toMatchObject({
      tone: "neutral",
      detail: "Último: no logrado",
    });
    const patched = liveSession("1", {
      attempts: [
        liveAttempt({
          outcome: "confirmed_violation",
          patched_by: { version: 4, seconds_after: 5 },
        }),
        liveAttempt({ id: "b", number: 2, outcome: "inconclusive" }),
      ],
    });
    expect(chatStatus(patched, true, false)).toMatchObject({
      tone: "blocked",
      detail: "Parche v4 vigente",
    });
  });

  it("el pulso del carrusel incluye el tono: un cambio de desenlace del Público se nota", () => {
    const audience = audienceSession("1", {
      attempts: [liveAttempt({ outcome: "confirmed_violation" })],
    });
    const item = carouselItem(audience, true, false);
    expect(item.tone).toBe("leak");
    expect(item.pulseKey).toBe("leak:1:evaluated");
    expect(item.short).toBe("Visitante-1");
  });

  it("acorta el alias del Prober con el final de su campaña", () => {
    const prober = liveSession("camp-3f2a", { kind: "prober", alias: "Prober · 3f2a" });
    expect(carouselItem(prober, true, false).short).toBe("P·3f2a");
  });

  it("mide el tiempo contra el reloj del servidor", () => {
    expect(ago("2026-10-24T15:00:59+00:00", NOW)).toBe("ahora");
    expect(ago("2026-10-24T15:00:30+00:00", NOW)).toBe("hace 30 s");
    expect(ago("2026-10-24T14:58:00+00:00", NOW)).toBe("hace 3 min");
  });
});

describe("escenario", () => {
  it("escala 1920 × 1080 a la ventana sin deformarlo", () => {
    expect(stageScale(1920, 1080)).toBe(1);
    expect(stageScale(960, 1080)).toBe(0.5);
    expect(stageScale(3840, 1080)).toBe(1);
    expect(stageScale(0, 0)).toBe(1);
  });
});
