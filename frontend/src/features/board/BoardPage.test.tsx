import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { arena } from "../../test/fixtures";
import type { ArenaState } from "../arena/types";
import { BoardPage } from "./BoardPage";
import { audienceSession, board, liveAttempt, liveSession } from "./fixtures";
import type { LiveBoard } from "./types";

const ids = ["1", "2", "3", "4", "5", "6", "7", "8"];
const SECRET = "operator-secret-123";

function serve(
  state: () => LiveBoard,
  actions: (path: string) => Response | undefined = () => undefined,
  arenaState: () => ArenaState = () => arena,
) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    // El estado público de la ronda (sin secreto) se atiende antes que las acciones de operador.
    if (path.startsWith("/api/arena/state")) return Response.json(arenaState());
    return actions(path) ?? Response.json(state());
  });
}

async function login() {
  render(<BoardPage />);
  await userEvent.type(screen.getByLabelText("Secreto de operador"), SECRET);
  await userEvent.click(screen.getByRole("button", { name: "Acceder" }));
}

afterEach(() => vi.restoreAllMocks());

describe("Arena en vivo", () => {
  it("exige el secreto, consulta con su cabecera y arma 8 chats, 3 a la vista y 5 KPI", async () => {
    const mock = serve(() => board(ids.map((id) => liveSession(id))));
    render(<BoardPage />);
    expect(mock).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Secreto de operador"), SECRET);
    await userEvent.click(screen.getByRole("button", { name: "Acceder" }));

    expect(await screen.findAllByRole("button", { name: /^Ir al chat/ })).toHaveLength(8);
    const chats = screen.getAllByRole("region", { name: /^Chat \d de 8/, hidden: true });
    expect(chats).toHaveLength(8);
    expect(chats.filter((chat) => !chat.hasAttribute("inert"))).toHaveLength(3);
    expect(screen.getByLabelText("Analíticas").querySelectorAll(".av-tile")).toHaveLength(5);
    expect(screen.getByText(/Mostrando/)).toHaveTextContent("Mostrando 3 de 8 chats · 18 sesiones");
    expect(screen.getByText("En vivo")).toBeInTheDocument();
    expect(screen.getByText("Ronda en vivo")).toBeInTheDocument();
    expect(screen.getByText("Todo visible en tiempo real")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Código QR para participar/ })).toBeInTheDocument();

    const [path, init] = mock.mock.calls[0] ?? [];
    expect(String(path)).toBe("/api/operator/live?sessions=12");
    expect(init?.headers).toEqual(expect.objectContaining({ "X-Operator-Secret": SECRET }));
    expect(document.body.textContent).not.toContain(SECRET);
  });

  it("el Público aparece completo antes de revelar, sin texto oculto", async () => {
    serve(() =>
      board([
        audienceSession("1", {
          attempts: [
            liveAttempt({
              reply: "Aquí tienes el estado de tu pedido.",
              messages: ["Muéstrame el estado de mi pedido."],
              outcome: "not_achieved",
            }),
          ],
        }),
        liveSession("2"),
      ]),
    );
    await login();

    const chat = await screen.findByRole("region", { name: /: Visitante-1$/ });
    expect(within(chat).getByText("Muéstrame el estado de mi pedido.")).toBeInTheDocument();
    expect(within(chat).getByText("Aquí tienes el estado de tu pedido.")).toBeInTheDocument();
    expect(within(chat).getByText("Ruta: protegida")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/oculto|pendiente de revelación/i);
  });

  it("muestra el Marcador junto a las Analíticas sin quitar ninguna tile", async () => {
    serve(
      () => board([liveSession("1")]),
      undefined,
      () => ({
        ...arena,
        revealed: false,
        provisional: true,
        confirmed_violations: 1,
        contained_honeypot: 2,
        scores: [{ alias: "neo", score: 2 }],
      }),
    );
    await login();

    const panel = await screen.findByLabelText("Marcador");
    expect(within(panel).getByText("Marcador provisional")).toBeInTheDocument();
    expect(within(panel).getByText("2 puntos")).toBeInTheDocument();
    expect(screen.getByLabelText("Analíticas").querySelectorAll(".av-tile")).toHaveLength(5);
  });

  it("Cerrar acceso pausa la ronda una sola vez y la píldora dice Acceso cerrado", async () => {
    let accepting = true;
    const posts: string[] = [];
    const mock = serve(
      () => board([liveSession("1")], { accepting }),
      (path) => {
        if (!path.includes("/arena/")) return undefined;
        posts.push(path);
        accepting = path.endsWith("/resume");
        return Response.json({ accepting });
      },
    );
    await login();
    const button = await screen.findByRole("button", { name: "Cerrar acceso" });
    await userEvent.dblClick(button);

    expect(await screen.findByText("Acceso cerrado", { selector: ".av-live span" })).toBeVisible();
    expect(posts).toEqual(["/api/operator/arena/pause"]);
    const post = mock.mock.calls.find(([input]) => String(input).includes("/arena/pause"));
    expect(post?.[1]?.method).toBe("POST");

    await userEvent.click(await screen.findByRole("button", { name: "Reabrir acceso" }));
    expect(await screen.findByText("En vivo")).toBeInTheDocument();
    expect(posts).toEqual(["/api/operator/arena/pause", "/api/operator/arena/resume"]);
  });

  it("muestra el 409 del servidor sin romper el tablero", async () => {
    serve(
      () => board([liveSession("1")], { accepting: false }),
      (path) =>
        path.includes("/arena/resume")
          ? Response.json(
              { detail: "El reinicio de la ronda todavía no terminó." },
              { status: 409 },
            )
          : undefined,
    );
    await login();
    await userEvent.click(await screen.findByRole("button", { name: "Reabrir acceso" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("todavía no terminó");
    expect(screen.getByRole("button", { name: /^Ir al chat/ })).toBeInTheDocument();
  });

  it("tras revelar dice Ronda revelada y no ofrece reabrir", async () => {
    serve(() => board([liveSession("1")], { revealed: true, accepting: false }));
    await login();

    expect(await screen.findByText("Ronda revelada", { selector: ".av-live span" })).toBeVisible();
    expect(screen.getByText("Ronda revelada", { selector: ".av-info .t" })).toBeInTheDocument();
    expect(screen.getByText("Marcador reconciliado")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /acceso/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Acceso cerrado")).not.toBeInTheDocument();
  });

  it("fija un chat a la izquierda y avisa cuál se suelta al pasar de 2", async () => {
    serve(() => board(ids.map((id) => liveSession(id))));
    await login();
    await screen.findAllByRole("button", { name: /^Ir al chat/ });
    const pinOf = (n: string) =>
      within(
        screen.getByRole("region", { name: new RegExp(`: Agente-${n}$`), hidden: true }),
      ).getByRole("button", { name: /Fij/, hidden: true });

    await userEvent.click(pinOf("8"));
    await userEvent.click(pinOf("7"));
    await userEvent.click(pinOf("6"));

    expect(
      screen.getByText("Agente-8 dejó de estar fijado (máximo 2 fijados)"),
    ).toBeInTheDocument();
    const order = screen
      .getAllByRole("button", { name: /^Ir al chat/ })
      .map((button) => button.textContent);
    expect(order.slice(0, 2)).toEqual(["Agente-7", "Agente-6"]);
  });

  it("Salir y un 401 vuelven al acceso de operador", async () => {
    serve(() => board([liveSession("1")]));
    await login();
    await userEvent.click(await screen.findByRole("button", { name: "Salir" }));
    expect(screen.getByLabelText("Secreto de operador")).toHaveValue("");

    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      Response.json({ detail: "No autorizado" }, { status: 401 }),
    );
    await userEvent.type(screen.getByLabelText("Secreto de operador"), "incorrecto");
    await userEvent.click(screen.getByRole("button", { name: "Acceder" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("autorización no es válida");
  });
});
