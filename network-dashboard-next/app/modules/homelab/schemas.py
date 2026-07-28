from __future__ import annotations

from pydantic import BaseModel, Field


class DeviceProfileUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    host: str = Field(min_length=1, max_length=253)
    ports: list[int] = Field(default_factory=list, max_length=30)
    mac: str = Field(default="", max_length=32)
    notes: str = Field(default="", max_length=1000)


class SubnetScanRequest(BaseModel):
    network: str = Field(min_length=1, max_length=64)
    ports: list[int] = Field(default_factory=lambda: [22, 80, 443], max_length=30)
    confirm: bool = False


class WakeOnLanRequest(BaseModel):
    mac: str = Field(min_length=1, max_length=32)
    broadcast: str = Field(default="255.255.255.255", min_length=1, max_length=64)
    port: int = Field(default=9, ge=1, le=65535)
    confirm: bool = False
