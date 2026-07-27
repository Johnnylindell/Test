from __future__ import annotations

from pydantic import BaseModel, Field


class BackupCreate(BaseModel):
    label: str = Field(default="manual", max_length=40)


class BackupRestore(BaseModel):
    confirm: bool = False
