import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ContractRegister } from "./ContractRegister";
import { clinicaSummary } from "./guardFixtures";

afterEach(() => vi.restoreAllMocks());

function setup(respond: (path: string, init: RequestInit) => Response) {
  const registered = vi.fn();
  const unauthorized = vi.fn(() => false);
  const mock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => respond(String(input), init ?? {}));
  render(<ContractRegister secret="s3" unauthorized={unauthorized} registered={registered} />);
  return { registered, mock };
}

describe("ContractRegister", () => {
  it("valida el YAML y muestra el resultado", async () => {
    const { mock } = setup(() => Response.json({ valid: true, contract: clinicaSummary }));
    await userEvent.type(screen.getByLabelText("Contrato en YAML"), "contract_id: x");
    await userEvent.click(screen.getByRole("button", { name: "Validar" }));
    expect(
      await screen.findByText(/Contrato válido: Recepción digital de una clínica/),
    ).toBeInTheDocument();
    const [path, init] = mock.mock.calls[0] ?? [];
    expect(path).toBe("/api/guard/contracts/validate");
    expect(init?.body).toBe("contract_id: x");
    expect(init?.headers).toEqual(expect.objectContaining({ "X-Operator-Secret": "s3" }));
  });

  it("muestra el error de un contrato inválido", async () => {
    setup(() => Response.json({ valid: false, error: "falta contract_id" }));
    await userEvent.type(screen.getByLabelText("Contrato en YAML"), "x: 1");
    await userEvent.click(screen.getByRole("button", { name: "Validar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Contrato inválido: falta contract_id",
    );
  });

  it("registra, avisa al padre y limpia el formulario", async () => {
    const { registered, mock } = setup(() =>
      Response.json({ contract: clinicaSummary }, { status: 201 }),
    );
    await userEvent.type(screen.getByLabelText("Contrato en YAML"), "contract_id: clinica-citas");
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));
    expect(await screen.findByText("Contrato clinica-citas registrado.")).toBeInTheDocument();
    expect(registered).toHaveBeenCalledWith(clinicaSummary);
    expect(mock.mock.calls[0]?.[0]).toBe("/api/guard/contracts");
    expect(screen.getByLabelText("Contrato en YAML")).toHaveValue("");
  });

  it("muestra el conflicto 409 del registro", async () => {
    const { registered } = setup(() =>
      Response.json({ detail: "El id pertenece a un contrato de archivo." }, { status: 409 }),
    );
    await userEvent.type(screen.getByLabelText("Contrato en YAML"), "contract_id: banco");
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("contrato de archivo");
    expect(registered).not.toHaveBeenCalled();
  });

  it("deshabilita las acciones con el YAML vacío", () => {
    setup(() => Response.json({}));
    expect(screen.getByRole("button", { name: "Validar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Registrar" })).toBeDisabled();
  });
});
