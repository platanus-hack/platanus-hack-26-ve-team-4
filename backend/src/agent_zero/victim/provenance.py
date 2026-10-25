import json
from typing import Any

from agent_zero.contract.provenance import origin


def _split_output(text: str) -> list[tuple[str, str]]:
    try:
        output = json.loads(text)
    except json.JSONDecodeError:
        return [("untrusted", text)]
    if not isinstance(output, dict):
        return [("store", text)]
    segments: list[tuple[str, str]] = []
    external = output.pop("untrusted_external_context", None)
    if isinstance(external, dict):
        segments.append(("untrusted", str(external.get("text", ""))))
    articles = output.get("articles")
    if isinstance(articles, list):
        trusted = []
        for article in articles:
            if isinstance(article, dict) and article.get("trust") == "untrusted":
                segments.append(("untrusted", str(article.get("text", ""))))
            else:
                trusted.append(article)
        output["articles"] = trusted
    segments.append(("store", json.dumps(output, ensure_ascii=False)))
    return segments


def _first_message(parts: list[dict[str, Any]]) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    for index, part in enumerate(parts):
        if "text" not in part:
            continue
        text = str(part["text"])
        if index == 0:
            try:
                header = json.loads(text)
            except json.JSONDecodeError:
                header = None
            if isinstance(header, dict) and "memoria_no_confiable" in header:
                # El titular sale del servidor (pedidos de la tienda); la memoria no es confiable.
                holder = header.get("cliente_autenticado")
                if isinstance(holder, dict):
                    segments.append(("store", json.dumps(holder, ensure_ascii=False)))
                memory = json.dumps(header["memoria_no_confiable"], ensure_ascii=False)
                segments.append(("memory", memory))
                continue
        segments.append(("user", text))
    return segments


def segments(conversation: list[dict[str, Any]]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for position, message in enumerate(conversation):
        if message.get("role") != "user":
            continue
        parts = list(message.get("content", []))
        if position == 0:
            found.extend(_first_message(parts))
            continue
        for part in parts:
            if "text" in part:
                found.append(("user", str(part["text"])))
            elif "toolResult" in part:
                for item in part["toolResult"].get("content", []):
                    if "text" in item:
                        found.extend(_split_output(str(item["text"])))
    return found


def trace_provenance(
    conversation: list[dict[str, Any]], arguments: dict[str, Any]
) -> tuple[tuple[str, str], ...]:
    found = segments(conversation)
    return tuple(sorted((name, origin(found, value)) for name, value in arguments.items()))
