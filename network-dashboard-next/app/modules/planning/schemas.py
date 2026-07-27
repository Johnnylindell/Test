from __future__ import annotations

from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    owner: str = Field(default="", max_length=80)
    remind_at: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=1000)


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    owner: str | None = Field(default=None, max_length=80)
    remind_at: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=1000)
    done: bool | None = None


class RoutineRuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    assigned_to: str = Field(default="", max_length=80)
    schedule: str = Field(default="", max_length=300)
    active: bool = True


class RoutineRuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    assigned_to: str | None = Field(default=None, max_length=80)
    schedule: str | None = Field(default=None, max_length=300)
    active: bool | None = None


class CompletionUpdate(BaseModel):
    done: bool
