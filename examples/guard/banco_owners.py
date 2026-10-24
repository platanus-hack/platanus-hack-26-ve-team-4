from __future__ import annotations

from typing import Any

ACCOUNTS = {"CTA-1": "ana", "CTA-2": "bruno"}


def owners(tool: str, arguments: dict[str, Any]) -> dict[str, str]:
    if "cuenta" not in arguments:
        return {}
    return {"cuenta": ACCOUNTS.get(str(arguments["cuenta"]), "desconocido")}
