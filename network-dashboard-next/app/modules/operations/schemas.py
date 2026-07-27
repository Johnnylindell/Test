from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ManagedServiceCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    unit_name: str = Field(min_length=9, max_length=180, pattern=r"^[A-Za-z0-9_.@-]+\.service$")


class ServiceAction(BaseModel):
    action: Literal["start", "stop", "restart"]
    confirm: bool = False


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class AgentHeartbeat(BaseModel):
    status: dict[str, Any] = Field(default_factory=dict)


class AgentCommandCreate(BaseModel):
    command_type: Literal["notify", "refresh_dashboard", "collect_status"]
    payload: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False


class AgentCommandResult(BaseModel):
    status: Literal["completed", "failed"]
    result: dict[str, Any] = Field(default_factory=dict)


class BaselineCreate(BaseModel):
    label: str = Field(default="Manuell baslinje", min_length=1, max_length=120)
