from agent_zero.policies.flow.dsl import Exceeds, FlowRule, NotSessionOwner, UntrustedOrigin

ORIGIN_LABELS = {
    "user": "mensaje del usuario",
    "store": "datos de la tienda",
    "untrusted": "documento o resultado no confiable",
    "memory": "memoria no confiable",
    "model": "sin origen observado",
}


def render(rule: FlowRule) -> str:
    condition = rule.deny_when
    if isinstance(condition, UntrustedOrigin):
        clause = f"{condition.argument} viene de una fuente no confiable"
    elif isinstance(condition, Exceeds):
        clause = f"{condition.argument} > {condition.limit:g}"
    elif isinstance(condition, NotSessionOwner):
        clause = "el pedido no es del cliente de la sesión"
    else:
        clause = "condición desconocida"
    return f"DENEGAR {rule.tool} SI {clause}"
