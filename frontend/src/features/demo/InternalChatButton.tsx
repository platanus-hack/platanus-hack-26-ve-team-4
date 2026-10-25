import { useState } from "react";
import { createPortal } from "react-dom";
import { LaunchDialog } from "./LaunchDialog";
import { useSwarm } from "./useSwarm";

export function InternalChatButton({ secret }: { secret: string }) {
  const swarm = useSwarm(secret);
  const [open, setOpen] = useState(false);
  const active = swarm.runs.filter((run) => run.phase !== "done" && run.phase !== "error").length;
  return (
    <>
      {swarm.running ? (
        <button type="button" className="av-btn-internal running" onClick={swarm.stop}>
          Detener chat interno ({active})
        </button>
      ) : (
        <button type="button" className="av-btn-internal" onClick={() => setOpen(true)}>
          Chat interno
        </button>
      )}
      {open &&
        createPortal(
          <LaunchDialog
            onClose={() => setOpen(false)}
            onLaunch={(ids) => {
              setOpen(false);
              swarm.launch(ids);
            }}
          />,
          document.body,
        )}
    </>
  );
}
