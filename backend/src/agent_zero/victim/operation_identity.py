import hashlib
import json
from typing import Any


def operation_fingerprint(tool: str, arguments: dict[str, Any], policy_version: int) -> str:
    content = {"tool": tool, "arguments": arguments, "policy_version": policy_version}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
