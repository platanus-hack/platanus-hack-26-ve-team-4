import asyncio
from datetime import timedelta
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.arena.core import ProductCore
from agent_zero.attempts.models import Attempt, AttemptStatus
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.policies.repository import PolicyRepository
from agent_zero.shared.clock import utc_now
from tests.arena.support import join

FINISHED = {AttemptStatus.EVALUATED, AttemptStatus.INCONCLUSIVE}


async def validated_policy(core: ProductCore) -> int:
    version = await core.policies.propose("finding-controlled", "OBJ-ORDER")
    assert version is not None
    await core.policies.start_validation(version)
    await core.policies.record_validation(version, {"passed": True})
    return version


async def stored(core: ProductCore, attempt_id: str) -> Attempt:
    async with core.fleet.database.sessions() as db:
        attempt = await AttemptRepository(db).get(attempt_id)
    assert attempt is not None
    return attempt


async def finished(core: ProductCore, attempt_id: str) -> Attempt:
    for _ in range(400):
        attempt = await stored(core, attempt_id)
        if attempt.status in FINISHED:
            return attempt
        await asyncio.sleep(0.01)
    raise AssertionError("El intento no terminó.")


def core_of(client: TestClient) -> ProductCore:
    return cast(ProductCore, cast(FastAPI, client.app).state.core)


def test_queued_attempts_wait_for_a_validated_patch_and_run_under_it(
    manual_client: TestClient,
) -> None:
    session = join(manual_client)
    core = core_of(manual_client)

    async def scenario() -> None:
        await core.worker.stop()
        version = await validated_policy(core)
        attempt = await core.submissions.submit(
            session["id"], AttemptCreate(message="Hola", idempotency_key="gate-wait")
        )
        assert attempt.policy_version == 0
        await asyncio.sleep(0.2)
        assert (await stored(core, attempt.id)).status is AttemptStatus.QUEUED
        assert not await core.attempts.drained()
        assert await core.attempts.none_running()
        assert await core.policies.activate(version, core.attempts.none_running)
        assert (await finished(core, attempt.id)).policy_version == version

    assert manual_client.portal is not None
    manual_client.portal.call(scenario)


def test_the_defense_loop_activates_while_new_attempts_keep_arriving(
    manual_client: TestClient,
) -> None:
    sessions = [join(manual_client, f"neo-{index}") for index in range(3)]
    core = core_of(manual_client)

    async def scenario() -> None:
        version = await validated_policy(core)
        ids = [
            (
                await core.submissions.submit(
                    session["id"],
                    AttemptCreate(message="Consulta", idempotency_key=f"gate-{session['id']}"),
                )
            ).id
            for session in sessions
        ]
        results = [await finished(core, attempt_id) for attempt_id in ids]
        assert [attempt.policy_version for attempt in results] == [version] * 3

    assert manual_client.portal is not None
    manual_client.portal.call(scenario)


def test_an_expired_hold_lets_attempts_run_under_the_active_policy(
    manual_client: TestClient,
) -> None:
    session = join(manual_client)
    core = core_of(manual_client)

    async def scenario() -> None:
        await core.worker.stop()
        version = await validated_policy(core)
        async with core.fleet.database.sessions() as db:
            row = await PolicyRepository(db).require(version)
            stale = utc_now() - timedelta(hours=1)
            row.validation = row.validation | {"validated_at": stale.isoformat()}
            await db.commit()
        attempt = await core.submissions.submit(
            session["id"], AttemptCreate(message="Hola", idempotency_key="gate-expired")
        )
        assert (await finished(core, attempt.id)).policy_version == 0

    assert manual_client.portal is not None
    manual_client.portal.call(scenario)
