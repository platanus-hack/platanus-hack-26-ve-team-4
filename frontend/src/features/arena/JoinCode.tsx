import QRCode from "qrcode";
import { useMemo, useState } from "react";

export function participantUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) return null;
    return new URL("/", url.origin).href;
  } catch {
    return null;
  }
}

export function JoinCode() {
  const [input, setInput] = useState(
    import.meta.env.VITE_PUBLIC_PARTICIPANT_URL || window.location.origin,
  );
  const url = participantUrl(input);
  const code = useMemo(() => {
    if (!url || url.length > 1000) return null;
    const qr = QRCode.create(url, { errorCorrectionLevel: "M" });
    const size = qr.modules.size;
    const cells: string[] = [];
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (qr.modules.get(y, x)) cells.push(`M${x + 4},${y + 4}h1v1h-1z`);
      }
    }
    return { size: size + 8, path: cells.join("") };
  }, [url]);
  const local = url && ["localhost", "127.0.0.1", "[::1]"].includes(new URL(url).hostname);
  return (
    <section className="join-card" aria-label="Participa en la arena">
      <div>
        <p className="eyebrow">Tu turno de explorar</p>
        <h2>Escanea y participa</h2>
        {url && (
          <a className="participant-link" href={url}>
            {url}
          </a>
        )}
        {local && (
          <p className="muted">
            Para abrir desde un teléfono, configura aquí la URL pública del despliegue.
          </p>
        )}
        <details>
          <summary>Configurar enlace público</summary>
          <label htmlFor="public-url">URL pública de esta arena</label>
          <input
            id="public-url"
            type="url"
            value={input}
            onChange={(event) => setInput(event.target.value)}
          />
          {!url && <p role="alert">Introduce una URL http o https válida, sin credenciales.</p>}
        </details>
      </div>
      {code && (
        <svg
          className="join-qr"
          role="img"
          aria-label={`Código QR para participar: ${url}`}
          viewBox={`0 0 ${code.size} ${code.size}`}
          shapeRendering="crispEdges"
        >
          <title>Escanea para abrir el chat de participantes</title>
          <path fill="#fff" d={`M0 0h${code.size}v${code.size}H0z`} />
          <path fill="#000" d={code.path} />
        </svg>
      )}
    </section>
  );
}
