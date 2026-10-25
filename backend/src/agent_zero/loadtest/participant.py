import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

import httpx

from agent_zero.loadtest.traffic import Task, is_honest, plan

FINAL = frozenset({"evaluated", "inconclusive"})
POLL_SECONDS = 0.5
ATTEMPT_TIMEOUT = 300.0
MAX_ADMISSION_WAIT = 600.0


@dataclass
class AttemptRecord:
    participant: str
    kind: str
    family: str
    attempt_id: str | None = None
    submitted: float = 0.0
    admitted: float = 0.0
    finished: float = 0.0
    status: str = "not_submitted"
    public_outcome: str | None = None
    throttled: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def latency(self) -> float | None:
        return self.finished - self.submitted if self.finished else None

    @property
    def run_seconds(self) -> float | None:
        return self.finished - self.admitted if self.finished else None


async def _submit(
    client: httpx.AsyncClient, token: str, task: Task, record: AttemptRecord
) -> str | None:
    body = {"messages": task.messages, "idempotency_key": f"stress-{uuid.uuid4().hex}"}
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.monotonic() + MAX_ADMISSION_WAIT
    while time.monotonic() < deadline:
        response = await client.post("/api/attempts", json=body, headers=headers)
        if response.status_code == 202:
            record.admitted = time.monotonic()
            attempt_id: str = response.json()["id"]
            return attempt_id
        if response.status_code == 429:
            record.throttled += 1
            await asyncio.sleep(float(response.headers.get("Retry-After", "2")))
            continue
        record.errors.append(f"submit {response.status_code}")
        return None
    record.errors.append("admission timeout")
    return None


async def _wait(
    client: httpx.AsyncClient, token: str, attempt_id: str, record: AttemptRecord
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.monotonic() + ATTEMPT_TIMEOUT
    while time.monotonic() < deadline:
        response = await client.get(f"/api/attempts/{attempt_id}", headers=headers)
        if response.status_code >= 500:
            record.errors.append(f"poll {response.status_code}")
        elif response.status_code == 200:
            view = response.json()
            if view["status"] in FINAL:
                record.finished = time.monotonic()
                record.status = view["status"]
                record.public_outcome = view.get("outcome")
                return
        await asyncio.sleep(POLL_SECONDS)
    record.status = "timeout"


Persona = Literal["mixed", "honest", "attacker"]


@dataclass(frozen=True)
class Pace:
    attempts: int
    think: float
    until: float | None = None


async def run_participant(
    client: httpx.AsyncClient,
    alias: str,
    pace: Pace,
    seed: int,
    persona: Persona = "mixed",
) -> list[AttemptRecord]:
    rng = random.Random(seed)
    attack_only = persona == "attacker"
    honest = persona == "honest" or (persona == "mixed" and is_honest(seed))
    failed = AttemptRecord(alias, "join", "join")
    try:
        joined = await client.post("/api/sessions", json={"alias": alias, "accepted_rules": True})
    except httpx.HTTPError as failure:
        failed.errors.append(f"join {type(failure).__name__}")
        return [failed]
    if joined.status_code != 201:
        failed.errors.append(f"join {joined.status_code}")
        return [failed]
    session = joined.json()
    records: list[AttemptRecord] = []
    for _ in range(pace.attempts):
        if pace.until is not None and time.monotonic() >= pace.until:
            break
        task = plan(session["order_ids"], rng, honest, attack_only)
        kind = "honest" if honest else task.kind
        record = AttemptRecord(alias, kind, task.family, submitted=time.monotonic())
        records.append(record)
        try:
            attempt_id = await _submit(client, session["token"], task, record)
            if attempt_id is not None:
                record.attempt_id = attempt_id
                await _wait(client, session["token"], attempt_id, record)
        except httpx.HTTPError as failure:
            record.errors.append(type(failure).__name__)
        await asyncio.sleep(rng.uniform(0, pace.think))
    return records
