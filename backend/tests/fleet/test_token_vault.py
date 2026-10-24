from datetime import timedelta

import pytest

from agent_zero.config import Settings
from agent_zero.fleet.token_vault import TokenNotFoundError, TokenVault
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.schemas import AgentGrant, IssuedCredential
from agent_zero.shared.classification import DataClassification
from tests.identity.conftest import FakeClock


def issue(clock: FakeClock) -> IssuedCredential:
    grant = AgentGrant(
        agent_id="agente-soporte",
        version="1.0.0",
        department="soporte",
        scopes=("tool:get_order",),
        clearance=DataClassification.INTERNAL,
        allowed_regions=("cl",),
    )
    return CredentialIssuer(Settings(environment="test"), clock).issue(grant)


def test_returns_token_until_it_expires() -> None:
    clock = FakeClock()
    vault = TokenVault(clock)
    credential = issue(clock)
    vault.put(credential)
    assert vault.token_for(credential.principal.credential_id) == credential.token
    clock.now += timedelta(days=1)
    assert vault.size() == 0
    with pytest.raises(TokenNotFoundError, match="credencial vigente"):
        vault.token_for(credential.principal.credential_id)


def test_put_purges_expired_entries() -> None:
    clock = FakeClock()
    vault = TokenVault(clock)
    vault.put(issue(clock))
    clock.now += timedelta(days=14)
    vault.put(issue(clock))
    assert vault.size() == 1
