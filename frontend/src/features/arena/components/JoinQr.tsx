import qrcode from "qrcode-generator";
import { useMemo } from "react";

// El QR lleva a la ruta de participantes ("/"), nunca a la de operación.
export function participantUrl(): string {
  return import.meta.env.VITE_PUBLIC_URL ?? `${window.location.origin}/`;
}

function svgFor(url: string): string {
  const code = qrcode(0, "M");
  code.addData(url);
  code.make();
  return code.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
}

export function JoinQr({ url = participantUrl() }: { url?: string }) {
  const svg = useMemo(() => svgFor(url), [url]);
  const written = url.replace(/^https?:\/\//, "");

  return (
    <section className="join" aria-labelledby="join-title">
      <h2 id="join-title">Únete a la ronda</h2>
      <div
        className="qr"
        role="img"
        aria-label={`Código QR hacia ${written}`}
        // El SVG lo genera qrcode-generator a partir de la URL; no contiene texto del usuario.
        // biome-ignore lint/security/noDangerouslySetInnerHtml: SVG generado localmente
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      <p className="join-link">{written}</p>
      <p className="muted">Simulación con datos ficticios. Usa un alias, sin datos personales.</p>
    </section>
  );
}
