import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ReplayStage } from "./ReplayStage";
import { replay, validated } from "./replayFixtures";

function motion(reduced: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({ matches: reduced, addEventListener: vi.fn() }),
  );
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ReplayStage", () => {
  it("no pide nada sin una validación aprobada", () => {
    const mock = vi.spyOn(globalThis, "fetch");
    render(<ReplayStage events={[validated(3, false)]} />);
    expect(mock).not.toHaveBeenCalled();
    expect(screen.queryByText("Repetición del ataque")).not.toBeInTheDocument();
  });

  it("con movimiento reducido salta al estado final en dos columnas", async () => {
    motion(true);
    const mock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json(replay));
    render(<ReplayStage events={[validated(2)]} />);
    expect(await screen.findByText("Política v1")).toBeInTheDocument();
    expect(screen.getByText("Política v2")).toBeInTheDocument();
    expect(String(mock.mock.calls[0]?.[0])).toBe("/api/arena/replay/2");
    expect(screen.getByText(/repetición de las llamadas a herramientas registradas/)).toBeVisible();
    expect(screen.getByText("El efecto indebido ocurrió.")).toBeInTheDocument();
    expect(await screen.findByText("Arista cortada.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("bloqueado por política v2");
    expect(screen.getByText("efecto indebido")).toBeInTheDocument();
    expect(screen.getByText("bloqueado")).toBeInTheDocument();
    expect(screen.getByText(/Consulta de un pedido propio/)).toBeInTheDocument();
    expect(screen.getByText(/Reembolso válido/)).toBeInTheDocument();
    expect(screen.getAllByText("permitida")).toHaveLength(2);
  });

  it("anima por fases: repetición, corte y sello", async () => {
    motion(false);
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json(replay));
    render(<ReplayStage events={[validated(2)]} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("Repitiendo las mismas llamadas…")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(screen.getByText("Arista cortada.")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1200);
    });
    expect(screen.getByRole("status")).toHaveTextContent("bloqueado por política v2");
    expect(screen.getByText("Tareas legítimas con la política v2")).toBeInTheDocument();
  });

  it("no muestra nada si la repetición no existe", async () => {
    motion(true);
    const mock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        Response.json({ detail: "No hay repetición para esa política." }, { status: 404 }),
      );
    render(<ReplayStage events={[validated(2)]} />);
    await vi.waitFor(() => expect(mock).toHaveBeenCalled());
    await act(async () => {});
    expect(screen.queryByText("Repetición del ataque")).not.toBeInTheDocument();
  });
});
