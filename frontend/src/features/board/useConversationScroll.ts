import {
  type KeyboardEvent,
  type RefObject,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

/** Margen (px) para considerar que el usuario está abajo del todo. */
export const BOTTOM_SLACK = 24;
/** Paso de ↑/↓ en px; AvPág/RePág usan max(LINE_STEP, clientHeight - LINE_STEP). */
export const LINE_STEP = 40;
/** Ventana (ms) en la que el scroll suave hacia el final ignora los eventos de scroll intermedios. */
const SEEK_MS = 700;

export interface ConversationScroll<T extends HTMLElement> {
  /** Ref del contenedor que se desplaza (el <ol className="av-conv">). */
  ref: RefObject<T | null>;
  /** Mensajes llegados mientras el usuario leía más arriba (0 si sigue al final). */
  unread: number;
  /** true si hay contenido por encima (scrollTop > 1): activa el degradado superior. */
  above: boolean;
  /** Para onScroll del contenedor. */
  onScroll: () => void;
  /** Para onKeyDown del contenedor: ↑ ↓ Inicio Fin AvPág RePág. */
  onKeyDown: (event: KeyboardEvent<T>) => void;
  /** Baja al final (suave salvo prefers-reduced-motion), pone unread en 0 y vuelve a seguir. */
  jumpToEnd: () => void;
}

const reducedMotion = () =>
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Conversación que sigue al último mensaje mientras el usuario está abajo y, si subió
 * para leer, cuenta los mensajes nuevos sin moverla. `count` es un contador monótono.
 */
export function useConversationScroll<T extends HTMLElement = HTMLElement>(
  count: number,
): ConversationScroll<T> {
  const ref = useRef<T | null>(null);
  const [unread, setUnread] = useState(0);
  const [above, setAbove] = useState(false);
  const stick = useRef(true);
  const lastCount = useRef(count);
  const seekUntil = useRef(0);

  // Corre en cada render: fija el final o cuenta los nuevos antes de pintar.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (stick.current) {
      el.scrollTop = el.scrollHeight;
    } else {
      const delta = count - lastCount.current;
      if (delta > 0) setUnread((u) => u + delta);
    }
    lastCount.current = count;
    const nowAbove = el.scrollTop > 1;
    if (nowAbove !== above) setAbove(nowAbove);
  });

  const onScroll = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    setAbove(el.scrollTop > 1);
    const bottom = el.scrollHeight - el.scrollTop - el.clientHeight <= BOTTOM_SLACK;
    if (!bottom && Date.now() < seekUntil.current) return;
    stick.current = bottom;
    if (bottom) {
      seekUntil.current = 0;
      setUnread(0);
    }
  }, []);

  const jumpToEnd = useCallback(() => {
    const el = ref.current;
    stick.current = true;
    setUnread(0);
    if (!el) return;
    if (reducedMotion() || typeof el.scrollTo !== "function") {
      el.scrollTop = el.scrollHeight;
      setAbove(el.scrollTop > 1);
    } else {
      seekUntil.current = Date.now() + SEEK_MS;
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, []);

  const onKeyDown = useCallback(
    (event: KeyboardEvent<T>) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const el = ref.current;
      if (!el) return;
      const page = Math.max(LINE_STEP, el.clientHeight - LINE_STEP);
      let top: number;
      switch (event.key) {
        case "ArrowUp":
          top = el.scrollTop - LINE_STEP;
          break;
        case "ArrowDown":
          top = el.scrollTop + LINE_STEP;
          break;
        case "PageUp":
          top = el.scrollTop - page;
          break;
        case "PageDown":
          top = el.scrollTop + page;
          break;
        case "Home":
          top = 0;
          break;
        case "End":
          top = el.scrollHeight;
          break;
        default:
          // ←/→ y el resto no se tocan: suben hasta window, donde el carrusel los usa.
          return;
      }
      event.preventDefault();
      el.scrollTop = top;
      seekUntil.current = 0;
      onScroll();
    },
    [onScroll],
  );

  // Un gesto del usuario cancela cualquier desplazamiento programado en curso.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const release = () => {
      seekUntil.current = 0;
    };
    el.addEventListener("wheel", release, { passive: true });
    el.addEventListener("touchstart", release, { passive: true });
    return () => {
      el.removeEventListener("wheel", release);
      el.removeEventListener("touchstart", release);
    };
  }, []);

  return { ref, unread, above, onScroll, onKeyDown, jumpToEnd };
}
