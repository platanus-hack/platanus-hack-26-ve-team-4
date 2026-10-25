import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { board, liveSession } from "../features/board/fixtures";
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
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      Response.json(board([liveSession("1")])),
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
