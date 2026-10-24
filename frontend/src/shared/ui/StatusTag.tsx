import type { Tone } from "../attemptLabels";

interface StatusTagProps {
  text: string;
  tone: Tone;
}

export function StatusTag({ text, tone }: StatusTagProps) {
  return <span className={`tag tag-${tone}`}>{text}</span>;
}
