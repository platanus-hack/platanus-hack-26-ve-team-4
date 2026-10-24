import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { arena, deferred } from "../../test/fixtures";
import { OperatorPage } from "./OperatorPage";

const policies = [
  { version: 0, status: "superseded", rules: [], reason: "Base", validation: {} },
  {
    version: 1,
    status: "active",
    rules: ["order_belongs_to_session_customer"],
    reason: "Verificar propietario",
    validation: { passed: true, cases: [{ name: "Consulta propia", passed: true }] },
  },
];
function mockOperator(
  action: (path: string, init: RequestInit) => Promise<Response> = async () => Response.json({}),
  options: { denied?: boolean; attempts?: unknown[] } = {},
) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path === "/api/arena/state") return Response.json(arena);
    if (path === "/api/guard/contracts") return Response.json([]);
    if (options.denied) return Response.json({ detail: "No autorizado" }, { status: 403 });
    if (init?.method === "POST") return action(path, init);
    if (path === "/api/operator/policies") return Response.json(policies);
    if (path === "/api/operator/attempts") return Response.json(options.attempts ?? []);
    if (
      path === "/api/operator/findings" ||
      path === "/api/operator/campaigns" ||
      path === "/api/operator/evaluations"
    )
      return Response.json([]);
    if (path.startsWith("/api/operator/attempts/")) return action(path, init ?? {});
    throw new Error(`Unexpected request: ${path}`);
  });
}
async function login() {
  await userEvent.type(screen.getByLabelText("Secreto de operador"), "operator-secret-123");
  await userEvent.click(screen.getByRole("button", { name: "Acceder" }));
}

describe("operación autorizada", () => {
  it("autoriza todas las lecturas y no persiste ni muestra el secreto", async () => {
    const mock = mockOperator();
    render(<OperatorPage />);
    await login();
    expect(
      await screen.findByRole("heading", { name: "Políticas y validación" }),
    ).toBeInTheDocument();
    for (const [path, init] of mock.mock.calls) {
      if (String(path).includes("/operator/"))
        expect(init?.headers).toEqual(
          expect.objectContaining({ "X-Operator-Secret": "operator-secret-123" }),
        );
    }
    expect(document.body.textContent).not.toContain("operator-secret-123");
    expect(JSON.stringify(sessionStorage)).not.toContain("operator-secret-123");
    expect(JSON.stringify(localStorage)).not.toContain("operator-secret-123");
    await userEvent.click(screen.getByRole("button", { name: "Cerrar acceso" }));
    expect(screen.getByLabelText("Secreto de operador")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Pausar entradas" })).not.toBeInTheDocument();
  });
  it("rechaza credenciales inválidas y borra acceso a controles", async () => {
    mockOperator(undefined, { denied: true });
    render(<OperatorPage />);
    await login();
    expect(await screen.findByRole("alert")).toHaveTextContent("autorización no es válida");
    expect(screen.getByLabelText("Secreto de operador")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Revelar clasificación" })).not.toBeInTheDocument();
  });
  it("serializa acciones incluso con doble click antes de respuesta", async () => {
    const response = deferred<Response>();
    const mock = mockOperator(() => response.promise);
    render(<OperatorPage />);
    await login();
    const button = await screen.findByRole("button", { name: "Pausar entradas" });
    act(() => {
      fireEvent.click(button);
      fireEvent.click(button);
    });
    expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Revelar clasificación" })).toBeDisabled();
    await act(async () => response.resolve(Response.json({ accepting: false })));
    expect(
      await screen.findByText("Entradas pausadas. Los intentos aceptados continúan."),
    ).toBeInTheDocument();
  });
  it("no repite silenciosamente una acción cuyo response se perdió", async () => {
    const mock = mockOperator(async () => {
      throw new TypeError("network down");
    });
    render(<OperatorPage />);
    await login();
    await userEvent.click(await screen.findByRole("button", { name: "Pausar entradas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No hay conexión");
    expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });
  it("muestra evidencia vinculada al intento y mantiene el replay explícito", async () => {
    const mock = mockOperator(
      async () =>
        Response.json({
          id: "attempt-evidence",
          status: "evaluated",
          route: "honeypot",
          policy_version: 1,
          outcome: "contained_honeypot",
          reply: "Datos fabricados",
          events: [
            {
              id: 2,
              type: "tool_completed",
              timestamp: "2026-10-24T00:00:00Z",
              data: { tool: "get_order", environment: "honeypot" },
            },
          ],
        }),
      {
        attempts: [
          {
            id: "attempt-evidence",
            status: "evaluated",
            route: "honeypot",
            policy_version: 1,
            outcome: "contained_honeypot",
            reply: "",
            origin: "audience",
          },
        ],
      },
    );
    render(<OperatorPage />);
    await login();
    await userEvent.click(await screen.findByRole("button", { name: "Ver evidencia" }));
    expect(await screen.findByRole("region", { name: "Evidencia del intento" })).toHaveTextContent(
      "Datos fabricados",
    );
    expect(screen.getByText("tool_completed")).toBeInTheDocument();
    expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  });
  it("exige motivo de reset y usa archivado del servidor", async () => {
    const mock = mockOperator(async () => Response.json({ archive_id: "archive-1" }));
    render(<OperatorPage />);
    await login();
    await userEvent.click(await screen.findByText("Archivar e iniciar otra ronda"));
    expect(screen.getByRole("button", { name: "Archivar e iniciar nueva ronda" })).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Motivo del nuevo ensayo"), "Ensayo jurado");
    await userEvent.click(screen.getByRole("button", { name: "Archivar e iniciar nueva ronda" }));
    expect(await screen.findByText(/Evidencia anterior archivada: archive-1/)).toBeInTheDocument();
    expect(mock).toHaveBeenCalledWith(
      "/api/operator/reset",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "Ensayo jurado" }),
      }),
    );
  });
  it("no revela ni reinicia mientras hay intentos pendientes", async () => {
    mockOperator(undefined, {
      attempts: [
        {
          id: "pending",
          status: "running",
          route: "protected",
          policy_version: 0,
          outcome: null,
          reply: "",
        },
      ],
    });
    render(<OperatorPage />);
    await login();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Revelar clasificación" })).toBeDisabled(),
    );
    await userEvent.click(screen.getByText("Archivar e iniciar otra ronda"));
    await userEvent.type(screen.getByLabelText("Motivo del nuevo ensayo"), "Reintento");
    expect(screen.getByRole("button", { name: "Archivar e iniciar nueva ronda" })).toBeDisabled();
  });
  it("lanza evaluación con versiones y presupuesto exactos solo por acción explícita", async () => {
    const mock = mockOperator();
    render(<OperatorPage />);
    await login();
    const button = await screen.findByRole("button", {
      name: "Comparar políticas · 90 ejecuciones",
    });
    expect(mock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
    await userEvent.click(button);
    expect(mock).toHaveBeenCalledWith(
      "/api/operator/evaluations",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          before_version: 0,
          after_version: 1,
          repetitions: 1,
          max_calls: 1200,
        }),
      }),
    );
  });
});
