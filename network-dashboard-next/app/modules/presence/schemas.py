from __future__ import annotations

from pydantic import BaseModel, Field


class PresenceDeviceCreate(BaseModel):
    owner: str = Field(min_length=1, max_length=80)
    label: str = Field(default="", max_length=120)
    source_id: str = Field(min_length=4, max_length=500)
    notify_arrival: bool = True


class PresenceObservation(BaseModel):
    source_id: str = Field(min_length=4, max_length=500)
    present: bool
    checked_at: str = Field(default="", max_length=80)
