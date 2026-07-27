from __future__ import annotations

from pydantic import BaseModel, Field


class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    start: str = Field(min_length=10, max_length=80)
    end: str = Field(min_length=10, max_length=80)
    description: str = Field(default="", max_length=4000)
    location: str = Field(default="", max_length=300)
    calendar_id: str = Field(default="primary", min_length=1, max_length=1000)


class GoogleTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    notes: str = Field(default="", max_length=4000)
    due: str = Field(default="", max_length=80)
    tasklist_id: str = Field(default="@default", max_length=300)


class GoogleTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    notes: str | None = Field(default=None, max_length=4000)
    due: str | None = Field(default=None, max_length=80)


class GoogleTaskCompletion(BaseModel):
    completed: bool = True


class GoogleTaskDelete(BaseModel):
    confirm: bool = False
