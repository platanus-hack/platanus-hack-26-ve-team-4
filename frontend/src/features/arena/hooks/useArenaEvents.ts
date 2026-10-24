import { useEffect, useState } from "react";
import type { ConnectionState, EventType, TraceEvent } from "../types";

const EVENT_TYPES: EventType[] = [
  "attempt_queued",
  "attempt_started",
  "attempt_completed",
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
  "probe_round_closed",
];

export function useArenaEvents(url = "/api/arena/events", limit = 100, roundId?: string) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");

  useEffect(() => {
    void roundId;
    setEvents([]);
    setConnection("connecting");
    if (typeof EventSource === "undefined") {
      setConnection("reconnecting");
      return;
    }
    const source = new EventSource(url);
    let active = true;
    const handleEvent = (message: MessageEvent<string>) => {
      if (!active) return;
      let event: TraceEvent;
      try {
        event = JSON.parse(message.data) as TraceEvent;
      } catch {
        return;
      }
      if (
        !event ||
        !Number.isSafeInteger(event.id) ||
        event.visibility !== "public" ||
        !EVENT_TYPES.includes(event.type)
      )
        return;
      setEvents((current) => {
        if (current.some((existing) => existing.id === event.id)) {
          return current;
        }
        return [event, ...current].sort((left, right) => right.id - left.id).slice(0, limit);
      });
    };
    source.onopen = () => {
      if (active) setConnection("open");
    };
    source.onerror = () => {
      if (active) setConnection("reconnecting");
    };
    for (const type of EVENT_TYPES) {
      source.addEventListener(type, handleEvent);
    }
    return () => {
      active = false;
      source.close();
    };
  }, [url, limit, roundId]);

  return { events, connection };
}
