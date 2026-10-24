from collections.abc import Callable

import pytest

from agent_zero.config import Settings
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.errors import VersionNotApprovedError
from agent_zero.registry.grant_service import grant_for
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.schemas import AgentManifest
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database


@pytest.mark.requirement("IDN-01", "REG-03")
async def test_grant_for_approved_version_feeds_issuer(
    database: Database, make_manifest: Callable[..., AgentManifest], registry_settings: Settings
) -> None:
    async with database.sessions() as db:
        await PublicationService(db).publish(make_manifest())
        await ApprovalService(db).approve("agente-finanzas", "1.0.0", "ana")
        grant = await grant_for(db, "agente-finanzas", "1.0.0")
    issued = CredentialIssuer(registry_settings).issue(grant)
    assert grant.department == "finanzas"
    assert grant.scopes == ("memory:read", "tool:get_invoice")
    assert grant.clearance is DataClassification.CONFIDENTIAL
    assert grant.allowed_regions == ("cl",)
    assert issued.principal.agent_id == "agente-finanzas"


@pytest.mark.requirement("IDN-01", "REG-03")
async def test_grant_for_draft_and_deprecated_is_denied(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    async with database.sessions() as db:
        await PublicationService(db).publish(make_manifest())
        with pytest.raises(VersionNotApprovedError):
            await grant_for(db, "agente-finanzas", "1.0.0")
        await ApprovalService(db).approve("agente-finanzas", "1.0.0", "ana")
        await ApprovalService(db).deprecate("agente-finanzas", "1.0.0")
        with pytest.raises(VersionNotApprovedError):
            await grant_for(db, "agente-finanzas", "1.0.0")
