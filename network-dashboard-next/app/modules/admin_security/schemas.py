from __future__ import annotations

from pydantic import BaseModel, Field


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=500)
    new_password: str = Field(min_length=8, max_length=500)


class AccessProfileUpdate(BaseModel):
    user: str = Field(min_length=1, max_length=40)
    sections: list[str] = Field(default_factory=list, max_length=100)
    readonly: bool = False


class RevokeSessions(BaseModel):
    keep_current: bool = True
