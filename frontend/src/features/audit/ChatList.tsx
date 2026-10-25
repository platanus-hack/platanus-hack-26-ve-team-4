import { useState } from "react";
import { KINDS, moment } from "./labels";
import type { ChatKind, ChatSummary } from "./types";

type Filter = "all" | ChatKind | "violations" | "honeypot";

const FILTERS: [Filter, string][] = [
  ["all", "Todos"],
  ["audience", "Público"],
  ["swarm", "Enjambre"],
  ["prober", "Prober"],
  ["test", "Pruebas"],
  ["violations", "Con violación"],
  ["honeypot", "Desviados"],
];

function matches(chat: ChatSummary, filter: Filter, query: string): boolean {
  const byFilter =
    filter === "all" ||
    chat.kind === filter ||
    (filter === "violations" && chat.violations > 0) ||
    (filter === "honeypot" && chat.route === "honeypot");
  const needle = query.trim().toLocaleLowerCase("es");
  const haystack = `${chat.alias} ${chat.id} ${chat.customer_id} ${chat.preview}`;
  return byFilter && (!needle || haystack.toLocaleLowerCase("es").includes(needle));
}

function tone(chat: ChatSummary): string {
  if (chat.violations) return "danger";
  if (chat.route === "honeypot") return "decoy";
  if (chat.outcomes.prevented) return "accent";
  return "muted";
}

export function ChatList({
  chats,
  selected,
  onSelect,
}: {
  chats: ChatSummary[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const list = chats.filter((chat) => matches(chat, filter, query));
  return (
    <aside className="monitor-panel audit-list" aria-label="Chats">
      <div className="monitor-row">
        <h2>Chats</h2>
        <span className="monitor-label">
          {list.length} de {chats.length}
        </span>
      </div>
      <label className="visually-hidden" htmlFor="audit-search">
        Buscar chat
      </label>
      <input
        id="audit-search"
        type="search"
        placeholder="Alias, sesión, cliente o mensaje"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <fieldset className="monitor-filters" aria-label="Filtrar chats">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className="monitor-chip"
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </fieldset>
      <div className="monitor-feed audit-feed">
        {list.map((chat) => (
          <button
            key={chat.id}
            type="button"
            className={`monitor-item tone-${tone(chat)}`}
            aria-current={chat.id === selected}
            onClick={() => onSelect(chat.id)}
          >
            <span className="monitor-item-top">
              <span>
                <b className="audit-alias">{chat.alias}</b> · {KINDS[chat.kind]}
              </span>
              <span>{moment(chat.last_activity)}</span>
            </span>
            <span className="monitor-item-msg">{chat.preview || "Sin mensajes"}</span>
            <span className="monitor-item-top">
              <span>
                {chat.attempts} mensajes · {chat.conversations} conversaciones
              </span>
              <span>
                {chat.violations > 0 &&
                  `${chat.violations} ${chat.violations === 1 ? "violación" : "violaciones"} · `}
                {chat.route === "honeypot" ? "señuelo" : "protegido"}
              </span>
            </span>
          </button>
        ))}
        {chats.length > 0 && list.length === 0 && (
          <p className="muted">Ningún chat coincide con el filtro.</p>
        )}
      </div>
    </aside>
  );
}
