from __future__ import annotations

from pydantic import BaseModel, Field


class ForgetItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=1000)
    due_at: str = Field(default="", max_length=80)
    owner: str = Field(default="", max_length=80)


class ForgetItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=1000)
    due_at: str | None = Field(default=None, max_length=80)
    owner: str | None = Field(default=None, max_length=80)
    done: bool | None = None


class QuestCompletion(BaseModel):
    done: bool = True
