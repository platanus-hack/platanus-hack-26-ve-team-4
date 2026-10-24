import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GuardPanel } from "./GuardPanel";
import {
  active,
  bancoSummary,
  clinicaSummary,
  findings,
  proposed,
  superseded,
} from "./guardFixtures";

afterEach(() => vi.restoreAllMocks());

function mockGuard(post: (path: string) => Response = () => Response.json({})) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (init?.method === "POST") return post(path);
    if (path === "/api/guard/contracts") return Response.json([bancoSummary, clinicaSummary]);
    if (path === "/api/guard/banco-transferencias/policies")
      return Response.json([superseded, active, proposed]);
    if (path === "/api/guard/banco-transferencias/findings") return Response.json(findings);
    if (path === "/api/guard/clinica-citas/policies") return Response.json([]);
    if (path === "/api/guard/clinica-citas/findings") return Response.json([]);
    throw new Error(`Unexpected request: ${path}`);
  });
}

describe("GuardPanel", () => {
  it("carga el primer contrato con políticas y hallazgos", async () => {
    const mock = mockGuard();
    render(<GuardPanel secret="op" logout={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: /Versión 2 · activa/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hallazgos del Guard · 2" })).toBeInTheDocument();
    for (const [, init] of mock.mock.calls)
      expect(init?.headers).toEqual(expect.objectContaining({ "X-Operator-Secret": "op" }));
  });

  it("cambia de contrato", async () => {
    mockGuard();
    render(<GuardPanel secret="op" logout={vi.fn()} />);
    await screen.findByRole("heading", { name: /Versión 2 · activa/ });
    await userEvent.selectOptions(screen.getByLabelText("Contrato"), "clinica-citas");
    expect(
      await screen.findByText("Este contrato aún no tiene versiones de política."),
    ).toBeInTheDocument();
  });

  it("activa una propuesta y avisa", async () => {
    const mock = mockGuard();
    render(<GuardPanel secret="op" logout={vi.fn()} />);
    await userEvent.click(await screen.findByRole("button", { name: "Activar versión 3" }));
    expect(await screen.findByText("Versión 3 activada.")).toBeInTheDocument();
    expect(mock).toHaveBeenCalledWith(
      "/api/guard/banco-transferencias/policies/3/activate",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("revierte la activa y muestra el 409", async () => {
    mockGuard(() => Response.json({ detail: "Estado no permitido." }, { status: 409 }));
    render(<GuardPanel secret="op" logout={vi.fn()} />);
    await userEvent.click(await screen.findByRole("button", { name: "Revertir versión 2" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Estado no permitido.");
  });

  it("cierra el acceso si el secreto no es válido", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({ detail: "No autorizado" }, { status: 403 }),
    );
    const logout = vi.fn();
    render(<GuardPanel secret="mal" logout={logout} />);
    await waitFor(() => expect(logout).toHaveBeenCalled());
  });

  it("explica el fallo de carga", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({ detail: "Caído" }, { status: 500 }),
    );
    render(<GuardPanel secret="op" logout={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Caído");
  });
});
