from __future__ import annotations

from pydantic import BaseModel, Field


class AssistantConfirmation(BaseModel):
    token: str = Field(min_length=20, max_length=5000)
