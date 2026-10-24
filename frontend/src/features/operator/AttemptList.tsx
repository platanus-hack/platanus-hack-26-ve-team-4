import type { OperatorAttempt } from "./api";

interface Props {
  attempts: OperatorAttempt[];
  inspect: (id: string) => Promise<void>;
  replay: (id: string) => Promise<void>;
}

export function AttemptList({ attempts, inspect, replay }: Props) {
  return (
    <section>
      <h2>Intentos</h2>
      {attempts
        .slice(-30)
        .reverse()
        .map((attempt) => (
          <article className="result" key={attempt.id}>
            <p>
              {attempt.id} · política {attempt.policy_version} · {attempt.route} ·{" "}
              {attempt.outcome ?? attempt.status}
            </p>
            <div className="controls">
              <button type="button" onClick={() => void inspect(attempt.id)}>
                Evidencia
              </button>
              <button type="button" onClick={() => void replay(attempt.id)}>
                Repetir en sesión limpia
              </button>
            </div>
          </article>
        ))}
    </section>
  );
}
