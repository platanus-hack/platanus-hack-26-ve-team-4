import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { session } from "../../test/fixtures";
import { TestChatPanel } from "./TestChatPanel";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("TestChatPanel", () => {
  it("abre el chat de prueba con el alias reservado", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(Response.json({ ...session, alias: "Interno-Fer" }));
    vi.spyOn(window, "open").mockReturnValue(null);
    render(<TestChatPanel secret="secreto" />);
    fireEvent.change(screen.getByLabelText("Nombre (opcional)"), { target: { value: "Fer" } });
    fireEvent.click(screen.getByRole("button", { name: "Abrir chat de prueba" }));
    expect(await screen.findByText(/Chat abierto como Interno-Fer/)).toBeInTheDocument();
    expect(JSON.parse(String(fetch.mock.calls[0]?.[1]?.body)).alias).toBe("Interno-Fer");
  });

  it("muestra el error si el servidor rechaza la sesión", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({ detail: "Las entradas de la ronda están cerradas." }, { status: 409 }),
    );
    render(<TestChatPanel secret="secreto" />);
    fireEvent.click(screen.getByRole("button", { name: "Abrir chat de prueba" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Las entradas de la ronda están cerradas.",
    );
  });
});
