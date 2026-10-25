import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { board, liveSession } from "../features/board/fixtures";
import { arena } from "../test/fixtures";
import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
  window.history.pushState({}, "", "/");
});

describe("rutas", () => {
  it("/arena pide el secreto de operador y deja la barra para ir a otros espacios", async () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    window.history.pushState({}, "", "/arena");
    render(<App />);

    expect(screen.getByRole("heading", { name: "Arena en vivo" })).toBeInTheDocument();
    expect(screen.getByLabelText("Secreto de operador")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Principal" })).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("al entrar con el secreto la barra se oculta y al Salir vuelve", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      Response.json(
        String(input).startsWith("/api/arena/state") ? arena : board([liveSession("1")]),
      ),
    );
    window.history.pushState({}, "", "/arena");
    render(<App />);

    await userEvent.type(screen.getByLabelText("Secreto de operador"), "operator-secret-123");
    await userEvent.click(screen.getByRole("button", { name: "Acceder" }));
    await screen.findByRole("button", { name: "Salir" });
    expect(screen.queryByRole("navigation", { name: "Principal" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Salir" }));
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(nav.querySelector('a[href="/operator"]')).not.toBeNull();
    expect(nav.querySelector('a[href="/"]')).not.toBeNull();
  });

  it("tras un 401 vuelve el acceso y la barra se ve otra vez", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      Response.json({ detail: "No autorizado" }, { status: 401 }),
    );
    window.history.pushState({}, "", "/arena");
    render(<App />);

    await userEvent.type(screen.getByLabelText("Secreto de operador"), "incorrecto");
    await userEvent.click(screen.getByRole("button", { name: "Acceder" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("autorización no es válida");
    // La limpieza del efecto corre tras el commit del 401: se espera a que la barra vuelva.
    const nav = await screen.findByRole("navigation", { name: "Principal" });
    expect(nav.querySelector('a[href="/monitor"]')).not.toBeNull();
    expect(nav.querySelector('a[href="/arena"]')).not.toBeNull();
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
