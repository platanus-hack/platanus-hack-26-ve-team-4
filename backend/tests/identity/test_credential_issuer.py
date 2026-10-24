from datetime import timedelta

import pytest

from agent_zero.config import Settings
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.schemas import AgentGrant
from tests.identity.conftest import FakeClock


@pytest.mark.requirement("IDN-01")
def test_issue_signs_short_lived_credential(
    identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    issued = CredentialIssuer(identity_settings, clock).issue(grant)

    payload, signature = issued.token.split(".")
    assert payload
    assert signature
    assert issued.principal.agent_id == "agent-soporte"
    assert issued.principal.version == "1.0.0"
    assert issued.principal.scopes == grant.scopes
    assert issued.principal.issued_at == clock.now
    assert issued.principal.expires_at == clock.now + timedelta(seconds=900)


@pytest.mark.requirement("IDN-01")
def test_each_credential_has_its_own_id(
    identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    issuer = CredentialIssuer(identity_settings, clock)
    assert (
        issuer.issue(grant).principal.credential_id != issuer.issue(grant).principal.credential_id
    )
