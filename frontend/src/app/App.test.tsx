import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
  window.history.pushState({}, "", "/");
});

describe("rutas", () => {
  it("/arena es la Arena en vivo detrás del acceso de operador y sin barra de navegación", () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    window.history.pushState({}, "", "/arena");
    render(<App />);

    expect(screen.getByRole("heading", { name: "Arena en vivo" })).toBeInTheDocument();
    expect(screen.getByLabelText("Secreto de operador")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Principal" })).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("el menú lleva a la Arena en vivo y ya no ofrece /tablero", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      Response.json({ detail: "sin datos" }, { status: 404 }),
    );
    window.history.pushState({}, "", "/");
    render(<App />);
    const nav = screen.getByRole("navigation", { name: "Principal" });

    expect(nav.querySelector('a[href="/arena"]')).toHaveTextContent("Arena en vivo");
    expect(nav.querySelector('a[href="/tablero"]')).toBeNull();
  });
});
