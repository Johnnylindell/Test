from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class WishlistCreate(BaseModel):
    member: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=180)
    url: HttpUrl | None = None
    note: str = Field(default="", max_length=1000)
    price: float | None = Field(default=None, ge=0)


class WishlistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    url: HttpUrl | None = None
    note: str | None = Field(default=None, max_length=1000)
    price: float | None = Field(default=None, ge=0)
    reserved_by: str | None = Field(default=None, max_length=80)
    purchased: bool | None = None
