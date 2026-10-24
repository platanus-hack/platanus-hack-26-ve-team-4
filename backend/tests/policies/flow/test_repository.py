import asyncio
from pathlib import Path

import pytest

from agent_zero.policies.flow.models import FlowPolicyRecord
from agent_zero.policies.flow.repository import flow_rules, flow_view
from agent_zero.policies.models import PolicyStatus, PolicyVersion
from agent_zero.policies.repository import PolicyRepository, content_hash
from agent_zero.shared.clock import utc_now
from agent_zero.shared.database import Database

RULE = {
    "rule_id": "ajeno",
    "tool": "get_order",
    "deny_when": {"kind": "not_session_owner"},
    "reason": "Pedido ajeno.",
}


def test_flow_rules_are_part_of_the_policy_hash(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")
        await database.create_schema()
        async with database.sessions() as db:
            await PolicyRepository(db).initialize()
            db.add(
                PolicyVersion(
                    version=1,
                    parent_version=0,
                    rules=[],
                    content_hash=content_hash([], 0, [RULE]),
                    status=PolicyStatus.CANDIDATE,
                    finding_ids=[],
                    reason="Flujo.",
                    validation={},
                    created_at=utc_now(),
                )
            )
            db.add(FlowPolicyRecord(version=1, rules=[RULE], synthesis={"status": "accepted"}))
            await db.commit()
            view = await PolicyRepository(db).view(1)
            assert (
                view["flow_rules"][0]["text"]
                == "DENEGAR get_order SI el pedido no es del cliente de la sesión"
            )
            assert [rule.rule_id for rule in await flow_rules(db, 1)] == ["ajeno"]
            record = await db.get(FlowPolicyRecord, 1)
            assert record is not None
            record.rules = [
                RULE | {"tool": "request_refund", "deny_when": {"kind": "not_session_owner"}}
            ]
            await db.commit()
            with pytest.raises(ValueError, match="alterada"):
                await PolicyRepository(db).require(1)
        await database.dispose()

    asyncio.run(scenario())


def test_versions_without_flow_rules_have_an_empty_view() -> None:
    assert flow_view(None) == {"flow_rules": [], "synthesis": None}
    assert content_hash(["a"], 0) == content_hash(["a"], 0, [])
