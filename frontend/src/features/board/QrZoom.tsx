import { useEffect, useState } from "react";
import { JoinQr, joinUrl } from "../arena/JoinCode";

/** QR de la cabecera: al hacerle clic se agranda al centro para que se escanee desde lejos. */
export function QrZoom() {
  const [open, setOpen] = useState(false);
  const url = joinUrl();
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  if (!url) return null;
  return (
    <>
      <button
        type="button"
        className="av-qr-btn"
        title="Agrandar el código QR"
        aria-label="Agrandar el código QR para participar"
        onClick={() => setOpen(true)}
      >
        <JoinQr className="av-qr" />
      </button>
      {open && (
        <div
          className="av-qr-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Código QR para participar"
        >
          <button
            type="button"
            className="av-qr-backdrop"
            aria-label="Cerrar el código QR"
            onClick={() => setOpen(false)}
          />
          <div className="av-qr-card">
            <JoinQr className="av-qr-big" />
            <p className="av-qr-title">Escanea para participar</p>
            <p className="av-qr-url">{url}</p>
            <button type="button" className="av-qr-close" onClick={() => setOpen(false)}>
              Cerrar
            </button>
          </div>
        </div>
      )}
    </>
  );
}
