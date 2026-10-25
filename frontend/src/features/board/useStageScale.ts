import { useEffect, useState } from "react";

export const STAGE = { width: 1920, height: 1080 };

/** Escala del escenario fijo para que entre completo en la ventana: min(w/1920, h/1080). */
export function stageScale(width: number, height: number): number {
  if (!(width > 0) || !(height > 0)) return 1;
  return Math.min(width / STAGE.width, height / STAGE.height);
}

export function useStageScale(): number {
  const [scale, setScale] = useState(() => stageScale(window.innerWidth, window.innerHeight));
  useEffect(() => {
    const update = () => setScale(stageScale(window.innerWidth, window.innerHeight));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  return scale;
}
