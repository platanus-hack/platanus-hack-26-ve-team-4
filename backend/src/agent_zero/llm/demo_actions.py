import json
import re
from typing import Any

from strands.types.content import Messages

ORDER_PATTERN = re.compile(r"\b[A-Z]-\d{4,9}\b", re.IGNORECASE)
MEMORY_PATTERN = re.compile(
    r"preferencia\s+([\w-]+)\s+con\s+valor\s+(.+)", re.IGNORECASE | re.DOTALL
)
AMOUNT_PATTERN = re.compile(
    r"(?:reembolsa(?:r)?|refund|amount)\s*[:=]?\s*(\d+(?:[.,]\d{1,2})?)", re.IGNORECASE
)


CREDENTIAL_PATTERN = re.compile(
    r"credencial|contraseña|clave\s+(?:de\s+)?(?:servicio|api)|api[\s_-]?key|admin", re.IGNORECASE
)
EXPORT_PATTERN = re.compile(
    r"export\w*|listado\s+completo|todos\s+los\s+clientes|volcado", re.IGNORECASE
)


def decoy_proposal(text: str, tools: frozenset[str]) -> list[tuple[str, dict[str, Any]]]:
    if "get_service_credentials" in tools and CREDENTIAL_PATTERN.search(text):
        return [("get_service_credentials", {})]
    if "export_customer_records" in tools and EXPORT_PATTERN.search(text):
        return [("export_customer_records", {})]
    return []


def propose(text: str, tools: frozenset[str] = frozenset()) -> list[tuple[str, dict[str, Any]]]:
    """Deterministic lab interpreter. Authorization always belongs to the real gateway."""
    memory = MEMORY_PATTERN.search(text)
    if memory:
        return [("save_memory", {"key": memory[1], "value": memory[2].strip().rstrip(".")})]
    orders = list(dict.fromkeys(match.upper() for match in ORDER_PATTERN.findall(text)))
    amount = AMOUNT_PATTERN.search(text)
    if orders and amount:
        return [
            (
                "request_refund",
                {"order_id": orders[0], "amount": float(amount[1].replace(",", "."))},
            )
        ]
    if orders:
        return [("get_order", {"order_id": order}) for order in orders]
    return decoy_proposal(text, tools) or [("search_knowledge", {"query": text[:4000] or "envío"})]


def result_texts(messages: Messages) -> list[str]:
    return [
        str(part["text"])
        for block in messages[-1]["content"]
        if "toolResult" in block
        for part in block["toolResult"]["content"]
        if "text" in part
    ]


def follow_untrusted(texts: list[str]) -> list[tuple[str, dict[str, Any]]]:
    """Intentionally vulnerable demonstration of an untrusted-source boundary."""
    proposals: list[tuple[str, dict[str, Any]]] = []
    for text in texts:
        try:
            output = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(output, dict):
            continue
        external = output.get("untrusted_external_context")
        sources = [external] if isinstance(external, dict) else []
        sources.extend(item for item in output.get("articles", []) if isinstance(item, dict))
        for source in sources:
            if source.get("trust") == "untrusted":
                proposals.extend(propose(str(source.get("text", ""))))
    return [proposal for proposal in proposals if proposal[0] != "search_knowledge"]


def already_proposed(messages: Messages, name: str, arguments: dict[str, Any]) -> bool:
    for message in reversed(messages):
        if message["role"] == "user" and any("text" in part for part in message["content"]):
            break
        for part in message["content"]:
            if "toolUse" in part:
                use = part["toolUse"]
                if use["name"] == name and use["input"] == arguments:
                    return True
    return False
