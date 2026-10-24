from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.shared.database import AppBase


class IdentityDenialReason(StrEnum):
    MALFORMED = "malformed"
    BAD_SIGNATURE = "bad_signature"
    EXPIRED = "expired"
    REVOKED = "revoked"
    MISSING_SCOPE = "missing_scope"


class RevokedCredential(AppBase):
    __tablename__ = "identity_revoked_credentials"

    credential_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RevokedAgent(AppBase):
    __tablename__ = "identity_revoked_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
