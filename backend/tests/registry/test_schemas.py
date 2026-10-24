from collections.abc import Callable

import pytest
from pydantic import BaseModel, ValidationError

from agent_zero.registry.schemas import AgentManifest


@pytest.mark.requirement("REG-01")
def test_manifest_normalizes_labels_and_scopes(make_manifest: Callable[..., AgentManifest]) -> None:
    manifest = make_manifest(
        capabilities=("B", " a ", "b"), scopes=("tool:z", "memory:read", "tool:z")
    )
    assert manifest.capabilities == ("a", "b")
    assert manifest.scopes == ("memory:read", "tool:z")


@pytest.mark.requirement("REG-01")
@pytest.mark.parametrize("version", ["1.0", "latest", "1.0.0.0", "01.0.0"])
def test_manifest_requires_strict_semver(
    make_manifest: Callable[..., AgentManifest], version: str
) -> None:
    with pytest.raises(ValidationError):
        make_manifest(version=version)


@pytest.mark.requirement("REG-01")
def test_manifest_rejects_bad_slug_and_extra_fields(
    make_manifest: Callable[..., AgentManifest],
) -> None:
    with pytest.raises(ValidationError):
        make_manifest(agent_id="Agente Finanzas")
    with pytest.raises(ValidationError):
        make_manifest(unexpected="x")


@pytest.mark.requirement("REG-01")
def test_manifest_is_frozen(make_manifest: Callable[..., AgentManifest]) -> None:
    manifest = make_manifest()
    with pytest.raises(ValidationError):
        BaseModel.__setattr__(manifest, "version", "2.0.0")
