import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RoundTimer } from "./RoundTimer";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

function advance(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

describe("RoundTimer", () => {
  it("empieza en 3:30 y descuenta al iniciar", () => {
    render(<RoundTimer />);
    expect(screen.getByRole("timer")).toHaveTextContent("03:30");

    fireEvent.click(screen.getByRole("button", { name: "Iniciar" }));
    advance(10_000);

    expect(screen.getByRole("timer")).toHaveTextContent("03:20");
  });

  it("se detiene al pausar y vuelve a 3:30 al reiniciar", () => {
    render(<RoundTimer />);
    fireEvent.click(screen.getByRole("button", { name: "Iniciar" }));
    advance(5_000);
    fireEvent.click(screen.getByRole("button", { name: "Pausar" }));
    advance(20_000);

    expect(screen.getByRole("timer")).toHaveTextContent("03:25");
    fireEvent.click(screen.getByRole("button", { name: "Reiniciar" }));
    expect(screen.getByRole("timer")).toHaveTextContent("03:30");
  });

  it("se queda en cero al terminar", () => {
    render(<RoundTimer durationMs={2_000} />);
    fireEvent.click(screen.getByRole("button", { name: "Iniciar" }));
    advance(5_000);

    expect(screen.getByRole("timer")).toHaveTextContent("00:00");
    expect(screen.getByRole("button", { name: "Iniciar" })).toBeDisabled();
  });
});
