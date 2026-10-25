import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Evidence } from "./api";
import { ACCESS_WITHOUT_DISCLOSURE_LABEL, EvidencePanel } from "./EvidencePanel";

function evidence(level: string, violated: boolean): Evidence {
  return {
    id: "attempt-1",
    status: "evaluated",
    route: "protected",
    policy_version: 1,
    outcome: "confirmed_violation",
    assessment: {
      verdicts: [{ objective_id: "order", violated, detail: "Lectura de pedido ajeno", level }],
    },
    events: [],
  } as Evidence;
}

describe("EvidencePanel", () => {
  it("etiqueta la violación de nivel acción sin divulgación", () => {
    render(<EvidencePanel evidence={evidence("action", true)} close={() => undefined} />);
    expect(screen.getByText(ACCESS_WITHOUT_DISCLOSURE_LABEL)).toBeInTheDocument();
  });
  it("no etiqueta una divulgación", () => {
    render(<EvidencePanel evidence={evidence("disclosure", true)} close={() => undefined} />);
    expect(screen.queryByText(ACCESS_WITHOUT_DISCLOSURE_LABEL)).not.toBeInTheDocument();
  });
  it("no etiqueta si no hubo violación", () => {
    render(<EvidencePanel evidence={evidence("action", false)} close={() => undefined} />);
    expect(screen.queryByText(ACCESS_WITHOUT_DISCLOSURE_LABEL)).not.toBeInTheDocument();
  });
});
