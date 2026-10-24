import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BoardPage } from "./BoardPage";
import { ChatTile } from "./ChatTile";
import { KpiColumn } from "./KpiColumn";
import { assignSlots } from "./slots";
import type { LiveAttempt, LiveBoard, LiveKpis, LiveSession } from "./types";

function liveAttempt(overrides: Partial<LiveAttempt> = {}): LiveAttempt {
  return {
    id: "att-1",
    status: "evaluated",
    outcome: "not_achieved",
    route: "protected",
    messages: ["Consulta mi pedido."],
    reply: "Aquí tienes tu pedido.",
    created_at: "2026-10-24T15:00:00+00:00",
    ...overrides,
  };
}
function liveSession(id: string, overrides: Partial<LiveSession> = {}): LiveSession {
  return {
    session_id: id,
    alias: `Agente-${id}`,
    kind: "swarm",
    route: "protected",
    customer_id: "cust-1",
    last_activity: `2026-10-24T15:00:0${id}+00:00`,
    attempt_total: 1,
    attempts: [liveAttempt({ id: `att-${id}` })],
    ...overrides,
  };
}
const kpis: LiveKpis = {
  attacks: { n: 9, audience: 3, swarm: 5, prober: 1, source: "x" },
  safe_space: {
    n: 6,
    diverted_sessions: 2,
    contained_attempts: 4,
    scope: "swarm_prober",
    label: "Solo enjambre y Prober hasta revelar",
    source: "x",
  },
  leaked: {
    n: 7,
    leaked: 3,
    by_objective: { "OBJ-ORDER": 3 },
    scope: "swarm_prober",
    label: "Solo enjambre y Prober hasta revelar",
    source: "x",
  },
  attacker_tokens: {
    measured: false,
    label: "no medido en modo demo",
    attacker: { measured: false, tokens: null, calls: 0 },
    decoy: { measured: false, tokens: null, calls: 0 },
    n: 0,
    source: "x",
  },
  patches: {
    n: 2,
    activated: 2,
    current_version: 2,
    median_seconds_to_patch: 75,
    findings_covered: 3,
    source: "x",
  },
};
function board(sessions: LiveSession[], overrides: Partial<LiveBoard> = {}): LiveBoard {
  return {
    revealed: false,
    llm_mode: "demo",
    policy_version: 2,
    sessions,
    kpis,
    generated_at: "2026-10-24T15:00:00+00:00",
    ...overrides,
  };
}

afterEach(() => vi.restoreAllMocks());

describe("tablero de ataque", () => {
  it("exige el secreto, consulta con su cabecera y dibuja seis chats y cinco analíticas", async () => {
    const mock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () =>
        Response.json(board(["1", "2", "3", "4", "5", "6"].map((id) => liveSession(id)))),
      );
    render(<BoardPage />);
    expect(mock).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Secreto de operador"), "operator-secret-123");
    await userEvent.click(screen.getByRole("button", { name: "Acceder" }));

    expect(await screen.findByLabelText("Chat de Agente-6")).toBeInTheDocument();
    expect(screen.getAllByLabelText(/^Chat de /)).toHaveLength(6);
    expect(screen.getByLabelText("Analíticas").querySelectorAll(".kpi")).toHaveLength(5);
    const [path, init] = mock.mock.calls[0] ?? [];
    expect(String(path)).toBe("/api/operator/live?sessions=12");
    expect(init?.headers).toEqual(
      expect.objectContaining({ "X-Operator-Secret": "operator-secret-123" }),
    );
    expect(document.body.textContent).not.toContain("operator-secret-123");
    expect(screen.getByRole("status")).toHaveTextContent("Antes de revelar");
  });

  it("vuelve al acceso cuando el servidor rechaza el secreto", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      Response.json({ detail: "No autorizado" }, { status: 401 }),
    );
    render(<BoardPage />);
    await userEvent.type(screen.getByLabelText("Secreto de operador"), "incorrecto");
    await userEvent.click(screen.getByRole("button", { name: "Acceder" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("autorización no es válida");
    expect(screen.getByLabelText("Secreto de operador")).toHaveValue("");
  });
});

describe("ChatTile", () => {
  it("rotula al enjambre como agente simulado y colorea según el desenlace", () => {
    const cases: [LiveSession, string][] = [
      [liveSession("1", { attempts: [liveAttempt({ outcome: "confirmed_violation" })] }), "leaked"],
      [liveSession("2", { route: "honeypot" }), "safe"],
      [liveSession("3", { attempts: [liveAttempt({ outcome: "prevented" })] }), "blocked"],
      [
        liveSession("4", { attempts: [liveAttempt({ status: "queued", outcome: null })] }),
        "neutral",
      ],
    ];
    for (const [session, state] of cases) {
      const { unmount } = render(
        <ChatTile session={session} pinned={false} onTogglePin={vi.fn()} />,
      );
      expect(screen.getByLabelText(`Chat de ${session.alias}`)).toHaveAttribute(
        "data-state",
        state,
      );
      expect(screen.getByText("Agente simulado")).toBeInTheDocument();
      unmount();
    }
  });

  it("muestra la transcripción, el desenlace y el escribiendo mientras corre", () => {
    const session = liveSession("1", {
      attempts: [
        liveAttempt({ messages: ["Primero.", "Segundo."], outcome: "prevented" }),
        liveAttempt({
          id: "att-b",
          status: "running",
          outcome: null,
          reply: "",
          messages: ["Otro."],
        }),
      ],
    });
    render(<ChatTile session={session} pinned={false} onTogglePin={vi.fn()} />);
    const transcript = screen.getByLabelText("Conversación de Agente-1");

    expect(within(transcript).getByText("Primero.")).toBeInTheDocument();
    expect(within(transcript).getByText("Segundo.")).toBeInTheDocument();
    expect(within(transcript).getByText("Aquí tienes tu pedido.")).toBeInTheDocument();
    expect(within(transcript).getByText("Detenido")).toBeInTheDocument();
    expect(within(transcript).getByText("Asistente escribiendo…")).toBeInTheDocument();
  });

  it("no muestra ruta ni violación del público antes de revelar", () => {
    const hidden = liveSession("1", {
      kind: "audience",
      alias: "neo",
      route: null,
      attempts: [liveAttempt({ route: null, outcome: "apparent_success" })],
    });
    render(<ChatTile session={hidden} pinned={false} onTogglePin={vi.fn()} />);

    expect(screen.getByText("Público")).toBeInTheDocument();
    expect(screen.queryByText("Protegido")).not.toBeInTheDocument();
    expect(screen.queryByText("Espacio seguro")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Chat de neo")).toHaveAttribute("data-state", "neutral");
    expect(screen.getByText("Éxito aparente")).toBeInTheDocument();
  });

  it("fija la sesión con un clic", async () => {
    const toggle = vi.fn();
    render(<ChatTile session={liveSession("1")} pinned={false} onTogglePin={toggle} />);
    await userEvent.click(screen.getByLabelText("Chat de Agente-1"));
    await userEvent.click(screen.getByRole("button", { name: "Fijar" }));

    expect(toggle).toHaveBeenCalledTimes(2);
    expect(toggle).toHaveBeenCalledWith("1");
  });
});

describe("KpiColumn", () => {
  it("no muestra un cero cuando los tokens no se midieron y declara su alcance y su n", () => {
    render(<KpiColumn kpis={kpis} />);
    const tokens = screen.getByLabelText("Tokens que gasta el atacante");

    expect(within(tokens).getByText("No medido")).toBeInTheDocument();
    expect(within(tokens).getByText("no medido en modo demo")).toBeInTheDocument();
    expect(within(tokens).queryByText("0")).not.toBeInTheDocument();
    expect(screen.getAllByText("Solo enjambre y Prober hasta revelar")).toHaveLength(2);
    expect(within(screen.getByLabelText("Ataques")).getByText(/n = 9/)).toBeInTheDocument();
    expect(within(screen.getByLabelText("Espacio seguro")).getByText("2/6")).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Ataques que dejamos pasar")).getByText("3"),
    ).toBeInTheDocument();
    expect(screen.getByText(/mediana hallazgo a parche 1 min 15 s/)).toBeInTheDocument();
  });

  it("muestra los tokens medidos cuando el ledger los tiene", () => {
    const measured: LiveKpis = {
      ...kpis,
      attacker_tokens: {
        measured: true,
        label: "",
        attacker: { measured: true, tokens: 12345, calls: 4 },
        decoy: { measured: true, tokens: 678, calls: 2 },
        n: 6,
        source: "x",
      },
    };
    render(<KpiColumn kpis={measured} />);
    const tokens = screen.getByLabelText("Tokens que gasta el atacante");

    expect(within(tokens).getByText(/12.345/)).toBeInTheDocument();
    expect(within(tokens).getByText(/Sostener el señuelo: 678 tokens/)).toBeInTheDocument();
    expect(within(tokens).queryByText("No medido")).not.toBeInTheDocument();
  });
});

describe("casillas", () => {
  const sessions = (...ids: string[]) =>
    new Map(ids.map((id) => [id, liveSession(id)] as [string, LiveSession]));

  it("conserva el lugar de cada sesión y completa los huecos", () => {
    expect(assignSlots(["2", "1"], sessions("1", "2", "3"), new Set(), 6)).toEqual(["2", "1", "3"]);
  });

  it("reemplaza la casilla más antigua sin fijar cuando todas están llenas", () => {
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
