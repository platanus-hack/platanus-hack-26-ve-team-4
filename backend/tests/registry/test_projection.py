from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from agent_zero.registry.hashing import canonical_manifest_json, sha256_of
from agent_zero.registry.models import AgentVersion, VersionStatus
from agent_zero.registry.projection import to_read
from agent_zero.registry.schemas import AgentManifest


@pytest.mark.requirement("REG-01")
def test_to_read_rebuilds_manifest(make_manifest: Callable[..., AgentManifest]) -> None:
    manifest = make_manifest()
    body = canonical_manifest_json(manifest)
    row = AgentVersion(
        agent_id=manifest.agent_id,
        version=manifest.version,
        department=manifest.department,
        status=VersionStatus.DRAFT,
        manifest_json=body,
        manifest_sha256=sha256_of(body),
        published_at=datetime(2026, 10, 24, tzinfo=UTC),
    )
    assert to_read(row).manifest == manifest
