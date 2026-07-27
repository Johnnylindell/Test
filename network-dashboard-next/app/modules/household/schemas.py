from __future__ import annotations

from pydantic import BaseModel, Field


class HouseholdItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=240)
    category: str = Field(default="", max_length=80)
    owner: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=1200)
    info: str = Field(default="", max_length=1200)
    image_url: str = Field(default="", max_length=800)


class HouseholdItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    location: str | None = Field(default=None, min_length=1, max_length=240)
    category: str | None = Field(default=None, max_length=80)
    owner: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=1200)
    info: str | None = Field(default=None, max_length=1200)
    image_url: str | None = Field(default=None, max_length=800)


class HouseholdPlaceUpsert(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    old_path: str = Field(default="", max_length=240)
    note: str = Field(default="", max_length=1200)
    info: str = Field(default="", max_length=1200)
    image_url: str = Field(default="", max_length=800)


class HouseholdLogCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    category: str = Field(default="Händelse", max_length=80)
    note: str = Field(default="", max_length=600)
