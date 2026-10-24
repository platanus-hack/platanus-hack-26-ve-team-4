from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    alias: str = Field(min_length=2, max_length=40, pattern=r"^[\w\- ]+$")


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alias: str
    created_at: datetime
