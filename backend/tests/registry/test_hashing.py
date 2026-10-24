import json
from collections.abc import Callable

import pytest

from agent_zero.registry.hashing import canonical_manifest_json, sha256_of
from agent_zero.registry.schemas import AgentManifest


@pytest.mark.requirement("REG-02")
def test_canonical_json_is_deterministic_and_sorted(
    make_manifest: Callable[..., AgentManifest],
) -> None:
    first = canonical_manifest_json(make_manifest())
    second = canonical_manifest_json(make_manifest())
    assert first == second
    keys = list(json.loads(first))
    assert keys == sorted(keys)


@pytest.mark.requirement("REG-02")
def test_hash_changes_with_any_field(make_manifest: Callable[..., AgentManifest]) -> None:
    base = sha256_of(canonical_manifest_json(make_manifest()))
    changed = sha256_of(canonical_manifest_json(make_manifest(description="Otra.")))
    assert len(base) == 64
    assert base != changed
