from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ControlledFixture(BaseModel):
    """Untrusted material installed only by the laboratory, never by audience input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    surface: Literal["document", "tool_result"]
    content: str = Field(min_length=1, max_length=8000)
    target_tool: Literal["search_knowledge", "get_order"] = "search_knowledge"
    source: Literal["lab:campaign", "lab:evaluation"] = "lab:campaign"
    query: str = Field(default="envío", min_length=1, max_length=200)
