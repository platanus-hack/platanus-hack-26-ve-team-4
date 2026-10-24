import json
from dataclasses import replace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.armor.model_armor import ModelArmor
from agent_zero.armor.models import ArmorAction, Surface
from agent_zero.decoy.session_trace import CREDENTIAL_TOOL
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.victim.arena_manifest import arena_manifest
from agent_zero.victim.honeytoken import HONEYTOKEN_PREFIX, honey_token
from agent_zero.victim.honeytool_schemas import HONEYTOOL_DESCRIPTIONS, HONEYTOOL_MODELS
from agent_zero.victim.honeytools import fake_records
from agent_zero.victim.tool_schemas import ARGUMENT_MODELS, parse_arguments, tool_specs

KEY = b"clave-de-prueba"


def test_honeytoken_is_deterministic_per_session_and_distinct_between_sessions() -> None:
    first = honey_token(KEY, "sess-a")

    assert first == honey_token(KEY, "sess-a")
    assert first != honey_token(KEY, "sess-b")
    assert first != honey_token(b"otra-clave", "sess-a")
    assert first.startswith(HONEYTOKEN_PREFIX)
    assert HONEYTOKEN_PREFIX.startswith("AZH")


def test_honeytoken_and_fake_records_survive_pii_redaction_and_output_armor() -> None:
    armor = ModelArmor()
    for index in range(300):
        session_id = f"sess-{index:04x}"
        payload = json.dumps(
            {
                "clave_api": honey_token(KEY, session_id),
                "registros": fake_records(session_id, 8),
            },
            ensure_ascii=False,
        )

        assert armor.redact_pii(payload) == payload, session_id
        assert armor.screen(payload, Surface.TOOL_OUTPUT).action is ArmorAction.ALLOW, session_id


def test_only_the_decoy_is_offered_and_granted_the_honeytools() -> None:
    protected = arena_manifest()
    decoy = arena_manifest(decoy=True)

    assert [spec["name"] for spec in tool_specs()] == list(ARGUMENT_MODELS)
    assert len(tool_specs()) == 4
    assert len(tool_specs(decoy=True)) == 6
    assert {tool.name for tool in protected.tools}.isdisjoint(HONEYTOOL_MODELS)
    assert not any(scope.removeprefix("tool:") in HONEYTOOL_MODELS for scope in protected.scopes)
    assert set(HONEYTOOL_MODELS) <= {tool.name for tool in decoy.tools}
    assert all(f"tool:{name}" in decoy.scopes for name in HONEYTOOL_DESCRIPTIONS)


def test_honeytool_arguments_are_closed() -> None:
    assert parse_arguments(CREDENTIAL_TOOL, {}) == {"service": "pasarela-reembolsos"}
    with pytest.raises(ValueError, match=r"."):
        parse_arguments(CREDENTIAL_TOOL, {"admin": True})


async def test_honeytools_refuse_to_run_outside_the_decoy(decoy_client: TestClient) -> None:
    honeytools = cast(FastAPI, decoy_client.app).state.core.honeytools
    principal = cast(AgentPrincipal, None)
    for environment in ("protected", "validation"):
        context = CallContext(
            attempt_id="att-1",
            session_id="sess-a",
            session_customer_id="cust-ana",
            environment=environment,
            policy_version=0,
            run_id="run-1",
        )
        with pytest.raises(ValueError, match="no disponible"):
            await honeytools.call(CREDENTIAL_TOOL, {}, context, principal)
    decoy = replace(context, environment="honeypot")
    output = json.loads((await honeytools.call(CREDENTIAL_TOOL, {}, decoy, principal)).text)
    assert output["clave_api"].startswith(HONEYTOKEN_PREFIX)
