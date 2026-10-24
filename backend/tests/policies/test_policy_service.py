from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from agent_zero.analyzer.finding_service import OBJECTIVE_TOOLS
from agent_zero.arena.core import ProductCore
from agent_zero.events.models import EventDelivery, EventRecord, EventType, Visibility
from agent_zero.policies.models import PolicyStatus
from agent_zero.policies.schemas import PolicyCandidate
from agent_zero.policies.validator_catalog import CONTROL_REASONS, OBJECTIVE_CONTROLS
from tests.policies.support import as_policy_candidate


@pytest.mark.parametrize("objective", sorted(OBJECTIVE_CONTROLS))
@pytest.mark.requirement("CORE-04")
def test_catalog_candidate_fits_the_contract_and_announces_patch_proposed(
    client: TestClient, objective: str
) -> None:
    core = cast(ProductCore, cast(FastAPI, client.app).state.core)
    finding_id = f"finding-{objective.lower()}"

    async def propose() -> tuple[int, dict[str, Any], list[tuple[EventRecord, EventDelivery]]]:
        # Without the worker, nobody moves the candidate to validation while it is read.
        await core.worker.stop()
        version = await core.policies.propose(finding_id, objective)
        assert version is not None
        # Only one candidate can be pending, so a second proposal is not announced.
        assert await core.policies.propose(finding_id, objective) is None
        view = await core.policies.get(version)
        async with core.fleet.database.sessions() as db:
            rows = await db.execute(
                select(EventRecord, EventDelivery)
                .join(EventDelivery, EventDelivery.event_id == EventRecord.id)
                .where(EventRecord.type == EventType.PATCH_PROPOSED)
            )
            return version, view, [(record, delivery) for record, delivery in rows]

    assert client.portal is not None
    version, view, proposed = client.portal.call(propose)
    assert len(proposed) == 1, proposed
    record, delivery = proposed[0]
    assert record.visibility is Visibility.PUBLIC
    assert record.policy_version == version
    assert record.data == {"version": version, "finding_id": finding_id}
    assert delivery.delivered_at is not None
    candidate = PolicyCandidate.model_validate(
        as_policy_candidate(view, OBJECTIVE_TOOLS[objective])
    )
    assert candidate.status is PolicyStatus.CANDIDATE
    assert candidate.parent_version == 0
    assert candidate.finding_ids == [finding_id]
    assert [rule.validator for rule in candidate.rules] == sorted(OBJECTIVE_CONTROLS[objective])
    assert candidate.reason == CONTROL_REASONS[objective]
