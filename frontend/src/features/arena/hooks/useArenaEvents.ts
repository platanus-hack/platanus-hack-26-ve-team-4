import { useEffect, useState } from "react";
import type { ConnectionState, EventType, TraceEvent } from "../types";

const EVENT_TYPES: EventType[] = [
  "attempt_queued",
  "attempt_started",
  "tool_proposed",
  "tool_denied",
  "tool_completed",
  "route_changed",
  "attempt_evaluated",
  "finding_opened",
  "patch_proposed",
  "patch_validated",
  "policy_activated",
  "policy_rolled_back",
];

export function useArenaEvents(url = "/api/arena/events", limit = 100) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");

  useEffect(() => {
    const source = new EventSource(url);
    const handleEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as TraceEvent;
      setEvents((current) => {
        if (current.some((existing) => existing.id === event.id)) {
          return current;
        }
        return [event, ...current].slice(0, limit);
      });
    };
    source.onopen = () => setConnection("open");
    source.onerror = () => setConnection("reconnecting");
    for (const type of EVENT_TYPES) {
      source.addEventListener(type, handleEvent);
    }
    return () => source.close();
  }, [url, limit]);

  return { events, connection };
}
