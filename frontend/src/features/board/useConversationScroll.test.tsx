/* biome-ignore-all lint/a11y/noNoninteractiveTabindex lint/a11y/noStaticElementInteractions: el arnés replica el contenedor enfocable de la conversación */
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useConversationScroll } from "./useConversationScroll";

const geom = { scrollHeight: 1000, clientHeight: 400 };

function Harness({ count }: { count: number }) {
  const conv = useConversationScroll<HTMLDivElement>(count);
  return (
    <>
      <div
        data-testid="conv"
        ref={conv.ref}
        tabIndex={0}
        onScroll={conv.onScroll}
        onKeyDown={conv.onKeyDown}
        data-above={String(conv.above)}
      />
      <output data-testid="unread">{conv.unread}</output>
      <button type="button" onClick={conv.jumpToEnd}>
        final
      </button>
    </>
  );
}

function conv(): HTMLDivElement {
  return screen.getByTestId("conv") as HTMLDivElement;
}

function unread(): string {
  return screen.getByTestId("unread").textContent ?? "";
}

/** Simula que el usuario desplaza la conversación hasta `top`. */
function scrollTo(top: number) {
  conv().scrollTop = top;
  fireEvent.scroll(conv());
}

beforeEach(() => {
  geom.scrollHeight = 1000;
  geom.clientHeight = 400;
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(
    () => geom.scrollHeight,
  );
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(
    () => geom.clientHeight,
  );
});

describe("useConversationScroll", () => {
  it("arranca pegado al final", () => {
    render(<Harness count={2} />);
    expect(conv().scrollTop).toBe(1000);
    expect(conv().dataset.above).toBe("true");
  });

  it("sigue al último mensaje mientras el usuario está abajo", () => {
    const { rerender } = render(<Harness count={2} />);
    geom.scrollHeight = 1200;
    rerender(<Harness count={4} />);
    expect(conv().scrollTop).toBe(1200);
    expect(unread()).toBe("0");
  });

  it("si el usuario subió no lo mueve y cuenta los nuevos", () => {
    const { rerender } = render(<Harness count={2} />);
    scrollTo(100);
    geom.scrollHeight = 1300;
    rerender(<Harness count={5} />);
    expect(conv().scrollTop).toBe(100);
    expect(unread()).toBe("3");
  });

  it("el margen de 24 px cuenta como abajo", () => {
    const { rerender } = render(<Harness count={2} />);
    scrollTo(1000 - 400 - 20);
    rerender(<Harness count={3} />);
    expect(unread()).toBe("0");
    geom.scrollHeight = 1100;
    rerender(<Harness count={4} />);
    expect(conv().scrollTop).toBe(1100);
  });

  it("volver abajo a mano pone el contador en 0", () => {
    const { rerender } = render(<Harness count={2} />);
    scrollTo(100);
    geom.scrollHeight = 1300;
    rerender(<Harness count={5} />);
    expect(unread()).toBe("3");
    // Con scrollHeight 1300 y clientHeight 400, scrollTop 900 deja el hueco en 0.
    scrollTo(900);
    expect(unread()).toBe("0");
  });

  it("jumpToEnd vuelve al final y limpia el contador", () => {
    const { rerender } = render(<Harness count={2} />);
    scrollTo(100);
    geom.scrollHeight = 1300;
    rerender(<Harness count={5} />);
    expect(unread()).toBe("3");
    fireEvent.click(screen.getByRole("button", { name: "final" }));
    expect(conv().scrollTop).toBe(1300);
    expect(unread()).toBe("0");
  });

  it("jumpToEnd usa scroll suave salvo movimiento reducido", () => {
    const original = HTMLElement.prototype.scrollTo;
    const scrollToSpy = vi.fn();
    HTMLElement.prototype.scrollTo = scrollToSpy;
    try {
      const { rerender } = render(<Harness count={2} />);
      scrollTo(100);
      geom.scrollHeight = 1300;
      rerender(<Harness count={5} />);
      fireEvent.click(screen.getByRole("button", { name: "final" }));
      expect(scrollToSpy).toHaveBeenCalledWith({ top: 1300, behavior: "smooth" });

      vi.stubGlobal("matchMedia", () => ({ matches: true }));
      scrollToSpy.mockClear();
      scrollTo(100);
      rerender(<Harness count={6} />);
      fireEvent.click(screen.getByRole("button", { name: "final" }));
      expect(scrollToSpy).not.toHaveBeenCalled();
      expect(conv().scrollTop).toBe(1300);
    } finally {
      vi.unstubAllGlobals();
      HTMLElement.prototype.scrollTo = original;
    }
  });

  it("teclas: Inicio, Fin, flechas y páginas desplazan", () => {
    render(<Harness count={2} />);
    fireEvent.keyDown(conv(), { key: "Home" });
    expect(conv().scrollTop).toBe(0);
    expect(conv().dataset.above).toBe("false");
    fireEvent.keyDown(conv(), { key: "ArrowDown" });
    expect(conv().scrollTop).toBe(40);
    fireEvent.keyDown(conv(), { key: "PageDown" });
    expect(conv().scrollTop).toBe(40 + 360);
    fireEvent.keyDown(conv(), { key: "End" });
    expect(conv().scrollTop).toBe(1000);
    fireEvent.keyDown(conv(), { key: "PageUp" });
    expect(conv().scrollTop).toBe(640);
  });

  it("ArrowLeft y ArrowRight no mueven la conversación ni se previenen", () => {
    render(<Harness count={2} />);
    const before = conv().scrollTop;
    expect(fireEvent.keyDown(conv(), { key: "ArrowLeft" })).toBe(true);
    expect(fireEvent.keyDown(conv(), { key: "ArrowRight" })).toBe(true);
    expect(conv().scrollTop).toBe(before);
  });

  it("el degradado superior solo aparece con contenido arriba", () => {
    render(<Harness count={2} />);
    scrollTo(0);
    expect(conv().dataset.above).toBe("false");
    scrollTo(50);
    expect(conv().dataset.above).toBe("true");
  });
});
