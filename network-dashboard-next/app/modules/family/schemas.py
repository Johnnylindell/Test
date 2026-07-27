from __future__ import annotations

from pydantic import BaseModel, Field


class AddFamilyListItem(BaseModel):
    list_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=300)
    owner: str = Field(default="", max_length=80)


class CompleteFamilyListItem(BaseModel):
    done: bool = True
