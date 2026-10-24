import { type FormEvent, useState } from "react";
import { createSession } from "./api/createSession";
import type { ArenaSession } from "./types";

export function ParticipantPage() {
  const [alias, setAlias] = useState("");
  const [session, setSession] = useState<ArenaSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      setSession(await createSession(alias));
    } catch {
      setError("No pudimos crear tu sesión. Revisa el alias e inténtalo de nuevo.");
    } finally {
      setPending(false);
    }
  }

  if (session) {
    return (
      <main className="page">
        <h1>Hola, {session.alias}</h1>
        <p>Tu sesión está lista. Estás en una simulación de seguridad con datos ficticios.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <h1>Agent Zero</h1>
      <p>
        Estás en una simulación de seguridad con datos ficticios. Usa un alias y evita introducir
        datos personales.
      </p>
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
        <button type="submit" disabled={pending}>
          {pending ? "Entrando…" : "Entrar a la arena"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
