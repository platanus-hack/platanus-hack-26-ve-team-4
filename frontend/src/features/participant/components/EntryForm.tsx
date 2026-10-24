import { type FormEvent, useState } from "react";
import { createSession } from "../api/createSession";
import { LEGITIMATE_EXAMPLE, OBJECTIVES, RULES } from "../rules";
import type { ArenaSession } from "../types";

interface EntryFormProps {
  onEnter: (session: ArenaSession) => void;
  expired: boolean;
}

export function EntryForm({ onEnter, expired }: EntryFormProps) {
  const [alias, setAlias] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      onEnter(await createSession(alias));
    } catch {
      setError("No pudimos crear tu sesión. Revisa el alias e inténtalo de nuevo.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="page entry">
      <h1>Agent Zero</h1>
      {expired && <p role="status">Tu sesión venció. Entra de nuevo para seguir participando.</p>}
      <p>{RULES}</p>
      <h2>Tres objetivos</h2>
      <ol>
        {OBJECTIVES.map((objective) => (
          <li key={objective}>{objective}</li>
        ))}
      </ol>
      <p className="muted">Una consulta legítima se ve así: «{LEGITIMATE_EXAMPLE}»</p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="alias">Alias</label>
        <input
          id="alias"
          value={alias}
          onChange={(event) => setAlias(event.target.value)}
          minLength={2}
          maxLength={40}
          required
        />
        <label className="check">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(event) => setAccepted(event.target.checked)}
            required
          />
          Acepto las reglas de la simulación
        </label>
        <button type="submit" disabled={pending || !accepted}>
          {pending ? "Entrando…" : "Entrar a la arena"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
