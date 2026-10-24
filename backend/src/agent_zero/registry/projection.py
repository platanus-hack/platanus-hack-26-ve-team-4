from agent_zero.registry.models import AgentVersion
from agent_zero.registry.schemas import AgentManifest, AgentVersionRead


def to_read(row: AgentVersion) -> AgentVersionRead:
    return AgentVersionRead(
        agent_id=row.agent_id,
        version=row.version,
        department=row.department,
        status=row.status,
        manifest=AgentManifest.model_validate_json(row.manifest_json),
        manifest_sha256=row.manifest_sha256,
        published_at=row.published_at,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        deprecated_at=row.deprecated_at,
    )
