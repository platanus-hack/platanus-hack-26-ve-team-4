import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { arena } from "../../test/fixtures";
import { ArenaPage } from "./ArenaPage";
import { JoinCode, participantUrl } from "./JoinCode";
import { Scoreboard } from "./Scoreboard";

describe("arena pública", () => {
  it("identifica evidencia simulada sin publicar resultados ocultos", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({
        ...arena,
        attempts: 14,
        audience_attempts: 10,
        autonomous_attempts: 4,
        scores: [{ alias: "neo", score: 2 }],
      }),
    );
    render(<ArenaPage />);
    expect(await screen.findByText("Demostración simulada.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Clasificación provisional" })).toBeInTheDocument();
    expect(screen.getByText("neo")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Métricas de la ronda" })).toHaveTextContent("14");
    expect(
      screen.queryByText(/contained_honeypot|confirmed_violation|AZP_|AZH_|cust-/),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Código QR para participar/ })).toBeInTheDocument();
  });
  it("separa clasificación final de puntos aparentes", () => {
    render(
      <Scoreboard
        arena={{
          ...arena,
          provisional: false,
          revealed: true,
          scores: [{ alias: "neo", score: 1 }],
        }}
      />,
    );
    expect(screen.getByRole("heading", { name: "Clasificación final" })).toBeInTheDocument();
    expect(screen.getByText(/Solo violaciones confirmadas/)).toBeInTheDocument();
    expect(screen.getByText("1 punto")).toBeInTheDocument();
  });
  it("muestra error visible sin inventar una clasificación", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("network offline"));
    render(<ArenaPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No hay conexión");
    expect(
      screen.queryByRole("heading", { name: "Clasificación provisional" }),
    ).not.toBeInTheDocument();
  });
  it("genera QR local y enlace de participación, elimina tokens y ruta de operación", async () => {
    const mock = vi.spyOn(globalThis, "fetch");
    render(<JoinCode />);
    await userEvent.click(screen.getByText("Configurar enlace público"));
    const input = screen.getByLabelText("URL pública de esta arena");
    await userEvent.clear(input);
    await userEvent.type(input, "https://arena.example/operator?token=secret#private");
    expect(screen.getByRole("link")).toHaveAttribute("href", "https://arena.example/");
    expect(screen.getByRole("img")).toHaveAttribute("viewBox");
    expect(screen.getByRole("img").querySelectorAll("path")).toHaveLength(2);
    expect(mock).not.toHaveBeenCalled();
  });
  it("rechaza protocolos ejecutables y URLs con credenciales", () => {
    expect(participantUrl("javascript:alert(1)")).toBeNull();
    expect(participantUrl("https://user:pass@arena.example/")).toBeNull();
    expect(participantUrl("https://arena.example/operator?secret=token")).toBe(
      "https://arena.example/",
    );
  });
});
