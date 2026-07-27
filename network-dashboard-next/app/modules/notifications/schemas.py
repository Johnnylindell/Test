from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=256)


class PushSubscription(BaseModel):
    endpoint: HttpUrl
    expirationTime: int | None = None
    keys: PushKeys


class PushSubscriptionRequest(BaseModel):
    subscription: PushSubscription


class AlertCreate(BaseModel):
    type: str = Field(default="info", max_length=60)
    message: str = Field(min_length=1, max_length=500)
    target: str = Field(default="all", max_length=80)
    severity: str = Field(default="normal", max_length=30)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationRule(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    event: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    target: str = Field(default="all", max_length=80)
    severity: str = Field(default="normal", max_length=30)
    template: str = Field(default="", max_length=500)
    cooldown_minutes: int = Field(default=0, ge=0, le=10080)
    conditions: dict[str, Any] = Field(default_factory=dict)


class NotificationRulesUpdate(BaseModel):
    rules: list[NotificationRule] = Field(default_factory=list, max_length=200)
