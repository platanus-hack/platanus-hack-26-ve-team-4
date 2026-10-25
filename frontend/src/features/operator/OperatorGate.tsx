import { type FormEvent, type ReactNode, useCallback, useState } from "react";

interface Props {
  children: (secret: string, logout: (message?: string) => void) => ReactNode;
}

/** Login de operador compartido. El secreto vive solo en memoria durante la visita. */
export function OperatorGate({ children }: Props) {
  const [input, setInput] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const logout = useCallback((message?: string) => {
    setSecret("");
    setInput("");
    setError(message ?? null);
  }, []);
  function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!input.trim()) return;
    setError(null);
    setSecret(input);
    setInput("");
  }
  if (secret) return <>{children(secret, logout)}</>;
  return (
    <>
      <p>
        Autoriza el acceso a trazas, controles, campañas y evidencia del laboratorio. El secreto
        permanece solo en memoria durante esta visita.
      </p>
      <form onSubmit={login}>
        <label htmlFor="operator-secret">Secreto de operador</label>
        <input
          id="operator-secret"
          type="password"
          autoComplete="off"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          required
        />
        <button type="submit">Acceder</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </>
  );
}
