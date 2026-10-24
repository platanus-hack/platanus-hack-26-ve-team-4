import type { ContractSummary, GuardFinding, GuardPolicy } from "./api";

export const bancoSummary: ContractSummary = {
  contract_id: "banco-transferencias",
  version: "1.0",
  name: "Asistente de banca personal",
  digest: "b93d0cca7dc648266659ae70011182a824f774e968534abb573eb9416d51e74f",
  tools: ["consultar_saldo", "leer_correo", "transferir"],
  invariants: ["cuentas-del-titular", "tope-por-transferencia", "beneficiarios-registrados"],
  legitimate: 4,
  auto_activate: true,
};

export const clinicaSummary: ContractSummary = {
  contract_id: "clinica-citas",
  version: "1.0",
  name: "Recepción digital de una clínica",
  digest: "9e06b7a68032bdb69f98833cf5b8d07169343e27e80794845301e5bd46040243",
  tools: ["agendar_cita", "enviar_mensaje", "ver_historia"],
  invariants: ["historia-del-propio-paciente", "especialidades-ofrecidas"],
  legitimate: 3,
  auto_activate: true,
};

export const superseded: GuardPolicy = {
  version: 1,
  parent_version: 0,
  status: "superseded",
  rules: [
    {
      rule_id: "r_transferir_tope_por_transferencia",
      tool: "transferir",
      deny_when: { argument: "monto", kind: "exceeds", limit: 500 },
      reason: "Ninguna transferencia del asistente supera 500 USD.",
      text: "DENEGAR transferir SI monto > 500",
    },
    {
      rule_id: "r_transferir_destino_untrusted",
      tool: "transferir",
      deny_when: { argument: "destino", kind: "untrusted_origin" },
      reason: "destino no lo pidió el sujeto: vino de una fuente no confiable.",
      text: "DENEGAR transferir SI destino viene de una fuente no confiable",
    },
  ],
  report: {
    llm_mode: "demo",
    violated: ["tope-por-transferencia", "beneficiarios-registrados"],
    source: "derived",
    gate: {
      accepted: true,
      original_blocked: 1,
      original_total: 1,
      legitimate_kept: 4,
      legitimate_total: 4,
      injected_blocked: 2,
      injected_total: 2,
    },
  },
  finding_id: "gf-715917f55f684ac38ce8",
  contract_digest: bancoSummary.digest,
  created_at: "2026-10-24T18:30:14.631548",
};

export const active: GuardPolicy = {
  ...superseded,
  version: 2,
  parent_version: 1,
  status: "active",
  rules: [
    ...superseded.rules,
    {
      rule_id: "r_transferir_cuentas_del_titular",
      tool: "transferir",
      deny_when: { argument: "cuenta", kind: "not_owner" },
      reason: "Solo se consultan o debitan cuentas del titular.",
      text: "DENEGAR transferir SI cuenta no pertenece al sujeto",
    },
  ],
  report: {
    ...superseded.report,
    gate: {
      accepted: true,
      original_blocked: 1,
      original_total: 1,
      legitimate_kept: 4,
      legitimate_total: 4,
      injected_blocked: 0,
      injected_total: 0,
    },
  },
  finding_id: "gf-9043f24939d64f97bab9",
  created_at: "2026-10-24T18:30:14.645642",
};

export const proposed: GuardPolicy = {
  ...active,
  version: 3,
  parent_version: 2,
  status: "proposed",
};

export const findings: GuardFinding[] = [
  {
    id: "gf-715917f55f684ac38ce8",
    call_id: "gc-c6f2ddd20e13419da9d6",
    invariant_ids: ["tope-por-transferencia", "beneficiarios-registrados"],
    policy_version: 0,
    resolved_by: 1,
    created_at: "2026-10-24T18:30:14.628488",
  },
  {
    id: "gf-9043f24939d64f97bab9",
    call_id: "gc-546e75881f2d473eb6e6",
    invariant_ids: ["cuentas-del-titular"],
    policy_version: 1,
    resolved_by: null,
    created_at: "2026-10-24T18:30:14.642903",
  },
];
