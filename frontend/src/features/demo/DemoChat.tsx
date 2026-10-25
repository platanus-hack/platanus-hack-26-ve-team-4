import { useEffect, useRef } from "react";
import type { LiveAttempt } from "../board/types";
import { denialLabel } from "../board/vocabulary";
import { richText } from "../participant/richText";
import { type DemoCase, kindOf, LEVELS } from "./catalog";
import type { ChatRun } from "./runner";
import type { Verdict } from "./verdict";
import "./demo-chat.css";

interface Props {
  item: DemoCase;
  run: ChatRun;
  live: Map<string, LiveAttempt>;
  verdict: Verdict;
}

function routeTag(attempt: LiveAttempt | undefined) {
  if (!attempt?.route) return null;
  return attempt.route === "honeypot" ? (
    <span className="demo-route r-honeypot">Señuelo</span>
  ) : (
    <span className="demo-route r-protected">Protegida</span>
  );
}

export function DemoChat({ item, run, live, verdict }: Props) {
  const scroller = useRef<HTMLDivElement>(null);
  const kind = kindOf(item);
  const size = run.turns.length + (run.turns.at(-1)?.attempt?.reply ? 1 : 0);

  useEffect(() => {
    void size;
    const node = scroller.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [size]);

  return (
    <article className={`demo-chat k-${kind} v-${verdict.tone}`} aria-label={run.alias}>
      <header>
        <span className={`demo-level l-${item.level}`}>N{item.level}</span>
        <div>
          <strong className="demo-title">
            {item.persona} · {item.title}
          </strong>
          <small>
            {LEVELS[item.level]} · {kind === "legit" ? "cliente legítimo" : "atacante"}
          </small>
        </div>
      </header>
      <div className="demo-thread" ref={scroller}>
        {run.turns.map((turn, index) => {
          const attempt = turn.attempt ? live.get(turn.attempt.id) : undefined;
          const reply = attempt?.reply || turn.attempt?.reply || "";
          const settled =
            turn.attempt?.status === "evaluated" || turn.attempt?.status === "inconclusive";
          return (
            // biome-ignore lint/suspicious/noArrayIndexKey: los turnos solo se agregan al final.
            <div key={`turn-${index + 1}`} className="demo-turn">
              <p className="demo-msg from-user">{turn.message}</p>
              {reply ? (
                <div className="demo-msg from-yummy">
                  {routeTag(attempt)}
                  <p>{richText(reply)}</p>
                  {attempt?.denials.length ? (
                    <small className="demo-denials">
                      Gateway negó: {attempt.denials.map(denialLabel).join(", ")}
                    </small>
                  ) : null}
                </div>
              ) : (
                !settled && <p className="demo-typing">Yummi está respondiendo…</p>
              )}
            </div>
          );
        })}
        {run.phase === "typing" && <p className="demo-typing user">Escribiendo…</p>}
        {run.phase === "creating" && <p className="demo-typing">Abriendo sesión…</p>}
        {run.error && <p role="alert">{run.error}</p>}
      </div>
      <footer>
        <span className={`demo-verdict v-${verdict.tone}`}>{verdict.label}</span>
        <small>
          Turno {Math.min(run.turns.length, item.turns.length)}/{item.turns.length}
        </small>
      </footer>
    </article>
  );
}
