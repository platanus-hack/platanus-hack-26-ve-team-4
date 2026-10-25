import { useEffect, useState } from "react";
import { errorMessage, requestJson } from "../../shared/api/http";
import type { Replay } from "../arena/replay/types";
import { operatorRequest } from "../operator/api";
import { AttemptReplay } from "./AttemptReplay";
import { clock, familyOf, NUMBER, ORIGINS, outcomeOf, patchDelay, tokensText } from "./labels";
import type { AttemptDetail, MonitorAttempt } from "./types";

function useDetail(secret: string, attempt: MonitorAttempt) {
  const [detail, setDetail] = useState<AttemptDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  // Se vuelve a pedir cuando el intento cambia de estado (cola → evaluado).
  useEffect(() => {
    void attempt.status;
    const controller = new AbortController();
    operatorRequest<AttemptDetail>(secret, `/attempts/${attempt.id}`, undefined, controller.signal)
      .then(setDetail)
      .catch((failure) => controller.signal.aborted || setError(failure));
    return () => controller.abort();
  }, [secret, attempt.id, attempt.status]);
  return { detail, error };
}

function useReplayOf(attempt: MonitorAttempt) {
  const [replay, setReplay] = useState<Replay | null>(null);
  const version =
    attempt.outcome === "confirmed_violation" && attempt.patch?.replay
      ? attempt.patch.version
      : null;
  useEffect(() => {
    if (version === null) return;
    const controller = new AbortController();
    requestJson<Replay>(`/api/arena/replay/${version}`, { signal: controller.signal })
      .then(setReplay)
      .catch(() => controller.signal.aborted || setReplay(null));
    return () => controller.abort();
  }, [version]);
  return version === null ? null : replay;
}

export function AttemptDetailPanel({
  secret,
  attempt,
}: {
  secret: string;
  attempt: MonitorAttempt;
}) {
  const { detail, error } = useDetail(secret, attempt);
  const replay = useReplayOf(attempt);
  const outcome = outcomeOf(attempt);
  const delay = patchDelay(attempt);
  const meta: [string, string][] = [
    ["Familia", familyOf(attempt)],
    ["Origen", ORIGINS[attempt.origin] ?? attempt.origin],
    ["Política", `v${attempt.policy_version}`],
    ["Tokens", tokensText(attempt)],
    ["Llamadas", NUMBER.format(attempt.usage.calls)],
    [
      "Duración",
      attempt.duration_seconds === null
        ? "—"
        : `${attempt.duration_seconds.toLocaleString("es", { maximumFractionDigits: 2 })} s`,
    ],
  ];
  if (attempt.patch) {
    meta.push([
      "Parche",
      `v${attempt.patch.version}${delay === null ? "" : ` activa ${delay} s después`}`,
    ]);
  }
  return (
    <section className="monitor-panel" aria-label="Detalle de la interacción">
      <div className="monitor-row">
        <div>
          <span className="monitor-label">
            Interacción {attempt.id} · {clock(attempt.created_at)}
          </span>
          <h2>{familyOf(attempt)}</h2>
        </div>
        <span className={`monitor-pill tone-${outcome.tone}`}>{outcome.label}</span>
      </div>
      <dl className="monitor-meta">
        {meta.map(([key, value]) => (
          <div key={key}>
            <dt className="monitor-label">{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <div className="monitor-convo">
        {attempt.messages.map((message, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: los turnos no tienen otro identificador.
          <p key={index} className="monitor-bubble is-user">
            {message}
          </p>
        ))}
        {detail?.reply && <p className="monitor-bubble is-bot">{detail.reply}</p>}
      </div>
      {error !== null && <p role="alert">{errorMessage(error)}</p>}
      {detail && <AttemptReplay attempt={attempt} graph={detail.graph} replay={replay} />}
    </section>
  );
}
