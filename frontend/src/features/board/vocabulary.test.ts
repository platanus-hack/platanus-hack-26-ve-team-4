import { describe, expect, it } from "vitest";
import { KIND } from "./vocabulary";

describe("KIND", () => {
  it("rotula el chat interno del equipo como prueba interna", () => {
    expect(KIND.test).toEqual({ label: "Prueba interna", cls: "test" });
  });

  it("mantiene el rótulo del público", () => {
    expect(KIND.audience.label).toBe("Público");
  });
});
