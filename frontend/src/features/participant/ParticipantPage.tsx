import { ChatView } from "./components/ChatView";
import { EntryForm } from "./components/EntryForm";
import { useStoredSession } from "./hooks/useStoredSession";

export function ParticipantPage() {
  const { session, save, expire, expired } = useStoredSession();

  if (!session) {
    return <EntryForm onEnter={save} expired={expired} />;
  }
  return <ChatView session={session} onExpired={expire} onLeave={() => save(null)} />;
}
