import { type FormEvent, useState } from "react";
import { MAX_TURN_CHARS, MAX_TURNS } from "../rules";

interface ComposerProps {
  sending: boolean;
  onSend: (messages: string[]) => Promise<boolean>;
}

export function Composer({ sending, onSend }: ComposerProps) {
  const [turns, setTurns] = useState<string[]>([""]);
  const ready = turns.every((turn) => turn.trim().length > 0);

  function update(index: number, value: string) {
    setTurns((current) => current.map((turn, i) => (i === index ? value : turn)));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (await onSend(turns.map((turn) => turn.trim()))) {
      setTurns([""]);
    }
  }

  return (
    <form className="composer" onSubmit={handleSubmit}>
      {turns.map((turn, index) => (
        // Los turnos solo se agregan o quitan al final, así que el índice es estable.
        // biome-ignore lint/suspicious/noArrayIndexKey: posición del turno en la secuencia
        <div className="turn" key={index}>
          <label htmlFor={`turn-${index}`}>
            Turno {index + 1}{" "}
            <span className="muted">
              ({turn.length}/{MAX_TURN_CHARS})
            </span>
          </label>
          <textarea
            id={`turn-${index}`}
            value={turn}
            maxLength={MAX_TURN_CHARS}
            rows={3}
            onChange={(event) => update(index, event.target.value)}
          />
        </div>
      ))}
      <div className="row">
        {turns.length < MAX_TURNS && (
          <button type="button" className="secondary" onClick={() => setTurns([...turns, ""])}>
            Añadir turno
          </button>
        )}
        {turns.length > 1 && (
          <button type="button" className="secondary" onClick={() => setTurns(turns.slice(0, -1))}>
            Quitar último turno
          </button>
        )}
        <button type="submit" disabled={sending || !ready}>
          {sending ? "Enviando…" : "Enviar intento"}
        </button>
      </div>
    </form>
  );
}
