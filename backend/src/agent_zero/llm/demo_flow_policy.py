from typing import Any

LOW_INTEGRITY = ("untrusted", "memory")


def demo_flow_policy(payload: dict[str, Any]) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    limit = float(payload["business_limits"]["refund_limit"])
    for call in payload["violating_calls"]:
        tool = str(call["tool"])
        provenance = dict(call.get("provenance") or {})
        candidates = ("amount", "order_id") if tool == "request_refund" else ("order_id",)
        low = next((arg for arg in candidates if provenance.get(arg) in LOW_INTEGRITY), None)
        if low is not None:
            rules.append(
                {
                    "rule_id": f"{tool}_{low}_untrusted",
                    "tool": tool,
                    "deny_when": {"kind": "untrusted_origin", "argument": low},
                    "reason": f"El argumento {low} proviene de contenido no confiable.",
                }
            )
        if tool == "request_refund":
            rules.append(
                {
                    "rule_id": "request_refund_over_limit",
                    "tool": tool,
                    "deny_when": {"kind": "exceeds", "argument": "amount", "limit": limit},
                    "reason": f"El reembolso supera {limit:g} USD.",
                }
            )
        rules.append(
            {
                "rule_id": f"{tool}_foreign_order",
                "tool": tool,
                "deny_when": {"kind": "not_session_owner"},
                "reason": "El pedido pertenece a otro cliente.",
            }
        )
    unique = list({rule["rule_id"]: rule for rule in rules}.values())[:3]
    return {
        "rules": unique,
        "rationale": (
            "Reglas derivadas por el modo demo a partir de la procedencia y los efectos de la "
            "traza; no es una síntesis de un proveedor."
        ),
    }
