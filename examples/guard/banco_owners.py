from __future__ import annotations

import os
from typing import Any

ACCOUNTS = {"CTA-1": os.environ.get("BANCO_TITULAR", "ana"), "CTA-2": "bruno"}


def owners(tool: str, arguments: dict[str, Any]) -> dict[str, str]:
    if "cuenta" not in arguments:
        return {}
    return {"cuenta": ACCOUNTS.get(str(arguments["cuenta"]), "desconocido")}
