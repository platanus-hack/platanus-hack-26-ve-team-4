from sqlalchemy import text

from agent_zero.shared.database import Database


async def escalate_clearance(database: Database) -> None:
    async with database.sessions() as db:
        await db.execute(
            text(
                "UPDATE registry_agent_versions SET manifest_json = "
                "replace(manifest_json, 'confidential', 'restricted')"
            )
        )
        await db.commit()
