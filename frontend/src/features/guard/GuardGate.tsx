import type { GateReport } from "./api";

export function GuardGate({ gate }: { gate?: GateReport }) {
  if (!gate) return <p className="muted">Sin informe de compuerta.</p>;
  return (
    <div className="guard-gate">
      <p>
        <strong>{gate.accepted ? "Compuerta aprobada" : "Compuerta rechazada"}</strong>
      </p>
      <ul>
        <li>
          Llamadas violatorias bloqueadas: {gate.original_blocked}/{gate.original_total}
        </li>
        <li>
          Tareas legítimas conservadas: {gate.legitimate_kept}/{gate.legitimate_total}
        </li>
        <li>
          Inyecciones simuladas bloqueadas: {gate.injected_blocked}/{gate.injected_total}
        </li>
      </ul>
    </div>
  );
}
