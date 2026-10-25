import { Fragment, type ReactNode } from "react";

// Markdown mínimo de las respuestas de Yummi: **negrita** y viñetas «- » o «* ». Se arma con
// elementos de React, sin HTML crudo, así que el texto del modelo nunca se interpreta como marcado.
// Los saltos de línea los conserva `white-space: pre-wrap` de la burbuja.

const BOLD = /\*\*(.+?)\*\*/g;
const BULLET = /^(\s*)[-*] (?=\S)/gm;

export function richText(text: string): ReactNode[] {
  const source = text.replace(BULLET, "$1• ");
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of source.matchAll(BOLD)) {
    const start = match.index ?? 0;
    if (start > last) parts.push(source.slice(last, start));
    parts.push(<strong key={start}>{match[1]}</strong>);
    last = start + match[0].length;
  }
  if (last < source.length) parts.push(source.slice(last));
  return parts.map((part, index) =>
    typeof part === "string" ? (
      // biome-ignore lint/suspicious/noArrayIndexKey: el orden de las partes es fijo por respuesta.
      <Fragment key={`t${index}`}>{part}</Fragment>
    ) : (
      part
    ),
  );
}
