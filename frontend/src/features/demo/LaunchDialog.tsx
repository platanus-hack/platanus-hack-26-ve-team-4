import { type FormEvent, useState } from "react";
import { CASES, caseById, kindOf, LEVELS, MAX_CHATS, RECOMMENDED } from "./catalog";
import "./dialog.css";

interface Props {
  onLaunch: (caseIds: string[]) => void;
  onClose: () => void;
}

export function LaunchDialog({ onLaunch, onClose }: Props) {
  const [count, setCount] = useState(MAX_CHATS);
  const [picks, setPicks] = useState<string[]>(RECOMMENDED);
  const chosen = picks.slice(0, count);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onLaunch(chosen);
  }

  function pick(index: number, id: string) {
    setPicks((current) => current.map((value, i) => (i === index ? id : value)));
  }

  return (
    <div className="demo-backdrop">
      <form
        className="demo-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="demo-dialog-title"
        onSubmit={submit}
      >
        <h2 id="demo-dialog-title">Lanzar chats automáticos</h2>
        <label htmlFor="demo-count">¿Cuántos chats a la vez?</label>
        <select
          id="demo-count"
          value={count}
          onChange={(event) => setCount(Number(event.target.value))}
        >
          {Array.from({ length: MAX_CHATS }, (_, i) => i + 1).map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <ol className="demo-picks">
          {chosen.map((id, index) => {
            const item = caseById(id);
            return (
              // biome-ignore lint/suspicious/noArrayIndexKey: cada fila es un puesto fijo del 1 al 6.
              <li key={`slot-${index + 1}`}>
                <label htmlFor={`demo-case-${index}`}>Chat {index + 1}</label>
                <select
                  id={`demo-case-${index}`}
                  value={id}
                  onChange={(event) => pick(index, event.target.value)}
                >
                  {CASES.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.id} · {LEVELS[option.level]} · {option.title}
                    </option>
                  ))}
                </select>
                <span className={`demo-kind k-${kindOf(item)}`}>
                  {kindOf(item) === "legit" ? "Cliente legítimo" : "Atacante"}
                </span>
              </li>
            );
          })}
        </ol>
        <div className="demo-dialog-actions">
          <button type="button" onClick={() => setPicks(RECOMMENDED)}>
            Usar los 6 recomendados
          </button>
          <button type="button" onClick={onClose}>
            Cancelar
          </button>
          <button type="submit">
            Lanzar {count} {count === 1 ? "chat" : "chats"}
          </button>
        </div>
      </form>
    </div>
  );
}
