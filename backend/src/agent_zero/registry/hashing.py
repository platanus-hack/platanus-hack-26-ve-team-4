import hashlib
import json

from agent_zero.registry.schemas import AgentManifest


def canonical_manifest_json(manifest: AgentManifest) -> str:
    return json.dumps(
        manifest.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_of(manifest_json: str) -> str:
    return hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
