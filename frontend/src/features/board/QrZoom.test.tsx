import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QrZoom } from "./QrZoom";

describe("QrZoom", () => {
  it("agranda el QR al hacer clic y lo cierra con el botón, el fondo o Escape", () => {
    render(<QrZoom />);
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Agrandar el código QR para participar" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Escanea para participar")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Agrandar el código QR para participar" }));
    fireEvent.click(screen.getByRole("button", { name: "Cerrar el código QR" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Agrandar el código QR para participar" }));
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
