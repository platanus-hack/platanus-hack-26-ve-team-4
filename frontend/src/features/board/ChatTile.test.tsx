import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { ChatTile, conversationCount } from "./ChatTile";
import { audienceSession, liveAttempt, liveSession, NOW } from "./fixtures";
import type { LiveAttempt, LiveSession } from "./types";

function tile(session: LiveSession, extra: Partial<Parameters<typeof ChatTile>[0]> = {}) {
  return render(
    <ChatTile
      session={session}
      index={0}
      total={8}
      pinned={false}
      inView
      accepting
      revealed={false}
      now={NOW}
      onTogglePin={vi.fn()}
      {...extra}
    />,
  );
}

describe("ChatTile", () => {
  it("rotula al enjambre, muestra la ruta y el pie sin inventar un total", () => {
    tile(liveSession("1", { last_activity: "2026-10-24T15:00:48+00:00" }));
    const chat = screen.getByLabelText("Chat 1 de 8: Agente-1");

    expect(within(chat).getByText("Agente simulado")).toBeInTheDocument();
    expect(within(chat).getByText("Ruta: protegida")).toBeInTheDocument();
    expect(chat).toHaveTextContent("Intento 1 · hace 12 s");
    expect(chat).not.toHaveTextContent(/Intento 1 de/);
  });

  it("pinta los desenlaces con el mapa OUTCOME y los objetivos violados", () => {
    const session = liveSession("1", {
      attempts: [
        liveAttempt({ id: "a", number: 1, outcome: "prevented", policy_version: 2 }),
        liveAttempt({ id: "b", number: 2, outcome: "contained_honeypot" }),
        liveAttempt({ id: "c", number: 3, outcome: null, status: "inconclusive" }),
        liveAttempt({
          id: "d",
          number: 4,
          outcome: "confirmed_violation",
          violated_objectives: ["OBJ-ORDER"],
        }),
      ],
    });
    tile(session);

    expect(screen.getByText("Intento 1 ·").parentElement).toHaveClass("o-blocked");
    expect(screen.getByText(/Bloqueado · parche v2/)).toBeInTheDocument();
    expect(screen.getByText(/Contenido/).closest("li")).toHaveClass("o-safe");
    expect(screen.getByText(/Inconcluso/).closest("li")).toHaveClass("o-incon");
    expect(screen.getByText(/Se filtró · OBJ-ORDER/).closest("li")).toHaveClass("o-leak");
    // Filtración sin parche: la franja queda en "Se filtró" hasta que llegue.
    expect(screen.getByLabelText("Chat 1 de 8: Agente-1")).toHaveAttribute("data-tone", "leak");
  });

  it("traduce las negaciones con DENIAL y cae a un texto legible si no las conoce", () => {
    tile(
      liveSession("1", {
        attempts: [
          liveAttempt({
            outcome: "prevented",
            denials: [
              {
                tool: "get_order",
                reason: "business_rule_denied",
                validator: "order_belongs_to_session_customer",
              },
              { tool: "refund", reason: "rate_limited", validator: null },
              { tool: "x", reason: "business_rule_denied", validator: "flow:cupo-diario" },
              { tool: "y", reason: "algo_nuevo", validator: null },
            ],
          }),
        ],
      }),
    );

    expect(screen.getByText("Herramienta negada · pedido ajeno")).toBeInTheDocument();
    expect(screen.getByText("Herramienta negada · límite de uso")).toBeInTheDocument();
    expect(screen.getByText("Herramienta negada · regla de flujo")).toBeInTheDocument();
    expect(screen.getByText("Herramienta negada · algo nuevo")).toBeInTheDocument();
  });

  it("muestra la técnica solo cuando el servidor la conoce", () => {
    tile(
      liveSession("1", {
        kind: "prober",
        alias: "Prober · 3f2a",
        attempts: [
          liveAttempt({ id: "a", technique: { family: "tool_misuse", mutator: "paraphrase_es" } }),
          liveAttempt({ id: "b", number: 2, technique: null }),
        ],
      }),
    );

    expect(screen.getByText("abuso de herramienta · paráfrasis")).toBeInTheDocument();
    expect(document.querySelectorAll(".av-tech")).toHaveLength(1);
  });

  it("marca el desvío a señuelo y el parche que cubrió la violación", () => {
    tile(
      liveSession("1", {
        route: "honeypot",
        contained_n: 1,
        attempts: [
          liveAttempt({
            id: "a",
            outcome: "confirmed_violation",
            violated_objectives: ["OBJ-MEMORY"],
            patched_by: { version: 3, seconds_after: 6.2 },
          }),
          liveAttempt({ id: "b", number: 2, route: "honeypot", outcome: "contained_honeypot" }),
        ],
      }),
    );

    expect(screen.getByText("Parche v3 activado · 6 s después")).toBeInTheDocument();
    expect(screen.getByText("Desviado a espacio seguro · int. 2")).toBeInTheDocument();
    expect(screen.getByText("En espacio seguro")).toBeInTheDocument();
    expect(screen.getByText("1 contenido")).toBeInTheDocument();
  });

  it("muestra al Público completo desde el primer intento", () => {
    const session = audienceSession("1", {
      route: "honeypot",
      attempts: [
        liveAttempt({
          outcome: "contained_honeypot",
          route: "honeypot",
          reply: "Aquí tienes el estado de tu pedido.",
          messages: ["Muéstrame el estado de mi pedido."],
          denials: [
            {
              tool: "get_order",
              reason: "business_rule_denied",
              validator: "order_belongs_to_session_customer",
            },
          ],
        }),
      ],
    });
    tile(session);
    const chat = screen.getByLabelText("Chat 1 de 8: Visitante-1");

    expect(within(chat).getByText("Muéstrame el estado de mi pedido.")).toBeInTheDocument();
    expect(within(chat).getByText("Aquí tienes el estado de tu pedido.")).toBeInTheDocument();
    expect(within(chat).getByText("Ruta: señuelo")).toBeInTheDocument();
    expect(within(chat).getByText("Herramienta negada · pedido ajeno")).toBeInTheDocument();
    expect(
      within(chat)
        .getByText(/Contenido/)
        .closest("li"),
    ).toHaveClass("o-safe");
    expect(within(chat).getByText("En espacio seguro")).toBeInTheDocument();
    expect(within(chat).getByText("Desviado a espacio seguro · int. 1")).toBeInTheDocument();
    expect(within(chat).queryByText("Respuesta oculta hasta revelar")).not.toBeInTheDocument();
    expect(within(chat).queryByText(/resultado oculto/)).not.toBeInTheDocument();
    expect(within(chat).queryByText("Oculto hasta revelar")).not.toBeInTheDocument();
    expect(chat).toHaveAttribute("data-tone", "safe");
    expect(chat.querySelectorAll(".av-seg.safe")).toHaveLength(1);
  });

  it("un Público con violación sin parche muestra el desenlace y el parche cuando llega", () => {
    tile(
      audienceSession("1", {
        attempts: [
          liveAttempt({
            outcome: "confirmed_violation",
            violated_objectives: ["OBJ-MEMORY"],
            patched_by: { version: 3, seconds_after: 6.2 },
          }),
          liveAttempt({ id: "b", number: 2, outcome: "confirmed_violation", route: "protected" }),
        ],
      }),
    );
    const chat = screen.getByLabelText("Chat 1 de 8: Visitante-1");

    expect(within(chat).getByText(/Se filtró · OBJ-MEMORY/)).toBeInTheDocument();
    expect(within(chat).getByText("Parche v3 activado · 6 s después")).toBeInTheDocument();
    expect(within(chat).queryByText("Oculto hasta revelar")).not.toBeInTheDocument();
    expect(chat).toHaveAttribute("data-tone", "leak");
  });

  it("muestra el escribiendo mientras el intento corre", () => {
    tile(
      liveSession("1", {
        attempts: [liveAttempt({ status: "running", outcome: null, reply: "" })],
      }),
    );

    expect(screen.getByText("Bot escribiendo…")).toBeInTheDocument();
    expect(document.querySelectorAll(".av-seg.run")).toHaveLength(1);
  });

  it("dice Acceso cerrado cuando la ronda está pausada y no hay intentos en curso", () => {
    tile(liveSession("1"), { accepting: false });
    expect(screen.getByText("Acceso cerrado")).toBeInTheDocument();
  });

  it("fija con el botón y queda fuera del orden de tabulación si no está a la vista", async () => {
    const toggle = vi.fn();
    const { rerender } = tile(liveSession("1"), { onTogglePin: toggle });
    await userEvent.click(screen.getByRole("button", { name: "Fijar" }));
    expect(toggle).toHaveBeenCalledWith("1");

    rerender(
      <ChatTile
        session={liveSession("1")}
        index={0}
        total={8}
        pinned
        inView={false}
        accepting
        revealed={false}
        now={NOW}
        onTogglePin={toggle}
      />,
    );
    expect(screen.getByLabelText("Chat 1 de 8: Agente-1")).toHaveAttribute("inert");
    expect(screen.getByText("Fijado").closest("button")).toHaveAttribute("aria-pressed", "true");
  });

  it("a una persona del Público se la rotula Participante y al enjambre Atacante", () => {
    const { unmount } = tile(liveSession("1", { kind: "audience", alias: "neo" }));
    const audience = screen.getByLabelText(/^Chat 1 de 8/);
    expect(within(audience).getByText("Participante")).toBeInTheDocument();
    expect(within(audience).queryByText("Atacante")).not.toBeInTheDocument();
    unmount();

    tile(liveSession("2"));
    const swarm = screen.getByLabelText(/^Chat 1 de 8/);
    expect(within(swarm).getByText("Atacante")).toBeInTheDocument();
    expect(within(swarm).queryByText("Participante")).not.toBeInTheDocument();
  });

  describe("conversación desplazable", () => {
    const attempts = (n: number, pendingLast = false): LiveAttempt[] =>
      Array.from({ length: n }, (_, k) =>
        liveAttempt({
          id: `a${k + 1}`,
          number: k + 1,
          messages: [`Mensaje ${k + 1}`],
          ...(pendingLast && k === n - 1 ? { status: "running", outcome: null, reply: "" } : {}),
        }),
      );
    const geom = { scrollHeight: 2000, clientHeight: 500 };
    function props(session: LiveSession) {
      return {
        session,
        index: 0,
        total: 8,
        pinned: false,
        inView: true,
        accepting: true,
        revealed: false,
        now: NOW,
        onTogglePin: vi.fn(),
      };
    }
    function conv(): HTMLOListElement {
      return screen.getByLabelText("Conversación de Agente-1") as HTMLOListElement;
    }

    beforeEach(() => {
      geom.scrollHeight = 2000;
      geom.clientHeight = 500;
      vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(
        () => geom.scrollHeight,
      );
      vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(
        () => geom.clientHeight,
      );
    });

    it("cuenta 2 por intento y resta 1 si el último sigue en curso", () => {
      expect(conversationCount([])).toBe(0);
      expect(conversationCount(attempts(3))).toBe(6);
      expect(conversationCount(attempts(3, true))).toBe(5);
    });

    it("dibuja todos los intentos recibidos, hasta el primero", () => {
      tile(liveSession("1", { attempts: attempts(12) }));
      expect(screen.getByText("Mensaje 1")).toBeInTheDocument();
      expect(screen.getByText("Mensaje 12")).toBeInTheDocument();
    });

    it("es enfocable, arranca al final y sin píldora", () => {
      tile(liveSession("1", { attempts: attempts(12) }));
      expect(conv()).toHaveAttribute("tabindex", "0");
      expect(conv().scrollTop).toBe(2000);
      expect(conv()).toHaveClass("above");
      expect(screen.queryByRole("button", { name: /Ir al último mensaje/ })).toBeNull();
    });

    it("sin contenido arriba no pinta el degradado", () => {
      // Como el navegador: scrollTop no pasa de scrollHeight - clientHeight.
      const original = Object.getOwnPropertyDescriptor(Element.prototype, "scrollTop");
      const tops = new WeakMap<Element, number>();
      Object.defineProperty(Element.prototype, "scrollTop", {
        configurable: true,
        get(this: Element) {
          return tops.get(this) ?? 0;
        },
        set(this: Element, top: number) {
          tops.set(this, Math.max(0, Math.min(top, geom.scrollHeight - geom.clientHeight)));
        },
      });
      onTestFinished(() => {
        if (original) Object.defineProperty(Element.prototype, "scrollTop", original);
      });
      geom.scrollHeight = 500;
      tile(liveSession("1", { attempts: attempts(1) }));
      expect(conv().scrollTop).toBe(0);
      expect(conv()).not.toHaveClass("above");
    });

    it("con el usuario arriba muestra ↓ N nuevos y al hacer clic vuelve al final", () => {
      const { rerender } = tile(liveSession("1", { attempts: attempts(5) }));
      fireEvent.keyDown(conv(), { key: "Home" });
      expect(conv().scrollTop).toBe(0);

      rerender(<ChatTile {...props(liveSession("1", { attempts: attempts(6, true) }))} />);
      expect(conv().scrollTop).toBe(0);
      expect(
        screen.getByRole("button", { name: "Ir al último mensaje: 1 nuevo" }),
      ).toHaveTextContent("↓ 1 nuevo");

      geom.scrollHeight = 2200;
      rerender(<ChatTile {...props(liveSession("1", { attempts: attempts(7) }))} />);
      const pill = screen.getByRole("button", { name: "Ir al último mensaje: 4 nuevos" });
      expect(pill).toHaveTextContent("↓ 4 nuevos");

      fireEvent.click(pill);
      expect(conv().scrollTop).toBe(2200);
      expect(screen.queryByRole("button", { name: /Ir al último mensaje/ })).toBeNull();
    });

    it("volver abajo a mano también quita la píldora", () => {
      const { rerender } = tile(liveSession("1", { attempts: attempts(5) }));
      fireEvent.keyDown(conv(), { key: "Home" });
      rerender(<ChatTile {...props(liveSession("1", { attempts: attempts(6) }))} />);
      expect(screen.getByRole("button", { name: /2 nuevos/ })).toBeInTheDocument();
      fireEvent.keyDown(conv(), { key: "End" });
      expect(screen.queryByRole("button", { name: /Ir al último mensaje/ })).toBeNull();
    });
  });
});
