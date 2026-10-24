import { OUTCOME_LABELS, STATUS_LABELS } from "../../../shared/attemptLabels";
import { StatusTag } from "../../../shared/ui/StatusTag";
import type { Attempt } from "../types";

export function AttemptItem({ attempt }: { attempt: Attempt }) {
  const status = STATUS_LABELS[attempt.status];
  const outcome = attempt.outcome ? OUTCOME_LABELS[attempt.outcome] : null;

  return (
    <li className="attempt">
      <div className="bubble mine">
        {attempt.messages.map((message, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: los turnos de un intento no cambian
          <p key={index}>{message}</p>
        ))}
      </div>
      {attempt.reply && <p className="bubble agent">{attempt.reply}</p>}
      <div className="row" aria-live="polite">
        <StatusTag text={status.text} tone={status.tone} />
        {outcome && <StatusTag text={outcome.text} tone={outcome.tone} />}
      </div>
    </li>
  );
}
