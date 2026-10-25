import type { Policy } from "../operator/api";
import { type Chapter, policyStory } from "./policyChapters";
import type { MonitorAttempt } from "./types";
import "./policy-story.css";

export const POLICY_STATUS: Record<string, string> = {
  active: "activa",
  candidate: "candidata",
  validating: "validando",
  superseded: "reemplazada",
  rejected: "rechazada",
  rolled_back: "revertida",
};

const STEPS = [
  "Un ataque logra algo que no debía",
  "La defensa escribe una regla para ese hueco",
  "La prueba contra el ataque y contra clientes legítimos",
  "Solo si pasa, la activa para todos",
];

function short(text: string, max = 180): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function Baseline({ chapter }: { chapter: Chapter }) {
  return (
    <li className="story-card is-base">
      <header>
        <span className="story-ver">v{chapter.version}</span>
        <b>Punto de partida</b>
        <small>{POLICY_STATUS[chapter.status] ?? chapter.status}</small>
      </header>
      <p>
        Sin reglas. El agente hace lo que le piden con sus herramientas: si alguien convence al
        modelo, nada lo detiene.
      </p>
    </li>
  );
}

function Learned({ chapter }: { chapter: Chapter }) {
  const blocked = chapter.adversarial;
  const kept = chapter.legitimate;
  return (
    <li className={`story-card is-${chapter.status}`}>
      <header>
        <span className="story-ver">v{chapter.version}</span>
        <b>{POLICY_STATUS[chapter.status] ?? chapter.status}</b>
        {chapter.learnedSeconds !== null && (
          <small>aprendida {Math.round(chapter.learnedSeconds)} s después del ataque</small>
        )}
      </header>
      <dl>
        <dt>Qué faltaba</dt>
        <dd>
          {chapter.rules.length
            ? chapter.rules.map((rule) => <p key={rule.code}>{rule.gap}</p>)
            : "Ajuste de reglas existentes."}
        </dd>
        {chapter.attack && (
          <>
            <dt>La conversación que lo reveló</dt>
            <dd>
              <q>{short(chapter.attack)}</q>
            </dd>
          </>
        )}
        <dt>Qué se creó</dt>
        <dd>
          {chapter.rules.map((rule) => (
            <p key={rule.code}>
              {rule.rule} <code>{rule.code}</code>
            </p>
          ))}
          {chapter.inherited.length > 0 && (
            <small className="story-muted">
              Conserva {chapter.inherited.length}{" "}
              {chapter.inherited.length === 1 ? "regla anterior" : "reglas anteriores"}.
            </small>
          )}
        </dd>
        {blocked.total + kept.total > 0 && (
          <>
            <dt>Cómo se probó antes de activarla</dt>
            <dd>
              Bloqueó {blocked.passed}/{blocked.total} repeticiones del ataque y {kept.passed}/
              {kept.total} casos de clientes legítimos siguieron funcionando.
            </dd>
          </>
        )}
        {chapter.effects.length > 0 && (
          <>
            <dt>Efecto</dt>
            <dd className="story-effects">
              {chapter.effects.map((effect) => (
                <span key={effect.label} className={effect.blocked ? "is-blocked" : ""}>
                  {effect.label}: antes ocurría →{" "}
                  {effect.blocked ? "ahora bloqueado" : "sin cambio"}
                </span>
              ))}
            </dd>
          </>
        )}
      </dl>
      {chapter.rationale && (
        <details>
          <summary>Explicación del analizador (asesoría)</summary>
          <p>{chapter.rationale}</p>
        </details>
      )}
    </li>
  );
}

export function PolicyStory({
  policies,
  attempts,
}: {
  policies: Policy[];
  attempts: MonitorAttempt[];
}) {
  const chapters = policyStory(policies, attempts);
  const learned = chapters.filter((chapter) => chapter.version > 0).length;
  return (
    <section className="monitor-panel story" aria-label="Cómo aprendió la defensa">
      <div className="story-intro">
        <h2>Cómo aprendió la defensa</h2>
        <p>
          <b>
            Una política es la lista de reglas que el gateway revisa antes de cada acción del agente
          </b>
          : consultar un pedido, reembolsar o guardar algo en memoria. No cambia ni reentrena el
          modelo; decide qué acciones se permiten. La ronda empieza en v0, sin reglas, y cada
          versión nueva cierra un hueco que un ataque real dejó al descubierto.
        </p>
        <ol className="story-steps">
          {STEPS.map((step, index) => (
            <li key={step}>
              <span>{index + 1}</span>
              {step}
            </li>
          ))}
        </ol>
        <p className="story-muted">
          {learned
            ? `${learned} ${learned === 1 ? "versión nueva" : "versiones nuevas"} en esta ronda.`
            : "Todavía no hay versiones nuevas: ningún ataque ha logrado nada en esta ronda."}
        </p>
      </div>
      <ol className="story-cards">
        {chapters.map((chapter) =>
          chapter.version === 0 ? (
            <Baseline key={chapter.version} chapter={chapter} />
          ) : (
            <Learned key={chapter.version} chapter={chapter} />
          ),
        )}
      </ol>
    </section>
  );
}
