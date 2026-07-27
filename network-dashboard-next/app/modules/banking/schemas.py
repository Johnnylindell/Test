from __future__ import annotations

from pydantic import BaseModel, Field


class BankRuleCreate(BaseModel):
    pattern: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=120)
    priority: int = Field(default=100, ge=0, le=10_000)
    active: bool = True
