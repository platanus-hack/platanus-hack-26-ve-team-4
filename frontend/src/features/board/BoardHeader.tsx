import type { ReactNode } from "react";
import { QrZoom } from "./QrZoom";
import type { LiveBoard } from "./types";

const EYE = (
  <>
    <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
    <circle cx="12" cy="12" r="3" />
  </>
);

interface Props {
  board: LiveBoard | null;
  chats: number;
  visible: number;
  busy: boolean;
  onToggleAccess: () => void;
  onExit: () => void;
  launcher?: ReactNode;
}

/** Píldora de estado: "En vivo", "Acceso cerrado" (pausa) o "Ronda revelada" (cerrada para siempre). */
export function livePill(board: LiveBoard | null): { text: string; cls: string } {
  if (!board) return { text: "Conectando…", cls: "closed" };
  if (board.revealed) return { text: "Ronda revelada", cls: "revealed" };
  if (!board.accepting) return { text: "Acceso cerrado", cls: "closed" };
  return { text: "En vivo", cls: "" };
}

export function BoardHeader({
  board,
  chats,
  visible,
  busy,
  onToggleAccess,
  onExit,
  launcher,
}: Props) {
  const pill = livePill(board);
  const revealed = board?.revealed ?? false;
  const closed = board ? !board.accepting : false;
  return (
    <header className="av-top">
      <h1 className="av-brand">
        <span className="av-mark" aria-hidden="true">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 2.5 4 6v6c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5V6l-8-3.5Z" />
            <path d="M8.5 12.5 11 15l4.5-5" />
          </svg>
        </span>
        <span>
          <span className="av-az">AGENT ZERO</span> · ARENA EN VIVO
        </span>
      </h1>
      <span className={`av-pill av-live ${pill.cls}`.trim()} role="status">
        <span className="av-dot" aria-hidden="true" />
        <span>{pill.text}</span>
      </span>
      <span className="av-pill">
        <b>{visible}</b> de <b>{chats}</b> chats · <b>{board?.sessions_total ?? 0}</b> sesiones
      </span>
      <span className="av-pill">
        Modelo: <b>{board ? (board.llm_mode === "demo" ? "demo" : "en vivo") : "—"}</b>
      </span>
      {launcher}
      <span className="av-spacer" />
      <div className={`av-info${revealed ? " revealed" : ""}`}>
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {EYE}
        </svg>
        <div>
          <div className="t">{revealed ? "Ronda revelada" : "Ronda en vivo"}</div>
          <div className="s">
            {revealed ? "Marcador reconciliado" : "Todo visible en tiempo real"}
          </div>
        </div>
      </div>
      <QrZoom />
      {/* Tras revelar la ronda no se puede reabrir: el servidor responde 409. */}
      {!revealed && (
        <button
          type="button"
          className={`av-btn-close${closed ? " closed" : ""}`}
          disabled={busy || !board}
          onClick={onToggleAccess}
        >
          {closed ? "Reabrir acceso" : "Cerrar acceso"}
        </button>
      )}
      <button type="button" className="av-exit" onClick={onExit}>
        Salir
      </button>
    </header>
  );
}
