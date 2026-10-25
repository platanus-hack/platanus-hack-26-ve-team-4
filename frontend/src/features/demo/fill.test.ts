import { describe, expect, it } from "vitest";
import { CASES } from "./catalog";
import { fill, placeholders } from "./fill";

describe("placeholders", () => {
  it("usa los pedidos de la sesión y a Carla como cliente ajeno", () => {
    const values = placeholders(["D-21001", "D-21002"]);
    expect(values).toMatchObject({
      own: "D-21001",
      own_delivered: "D-21002",
      own_total: "45",
      own_delivered_total: "18",
      f: "C-3001",
      f_name: "Carla Méndez",
      g_delivered: "B-2002",
    });
  });

  it("cambia de cliente ajeno si la sesión es de Carla o de Bruno", () => {
    expect(placeholders(["C-3001", "C-3002"])).toMatchObject({ f: "A-1001", f_name: "Ana Rojas" });
    expect(placeholders(["B-2001", "B-2002"]).g_delivered).toBe("A-1002");
  });

  it("ningún caso deja marcadores sin rellenar", () => {
    const values = placeholders(["D-21001", "D-21002"]);
    for (const item of CASES)
      for (const turn of item.turns) expect(fill(turn, values)).not.toMatch(/\{\w+\}/);
  });
});
