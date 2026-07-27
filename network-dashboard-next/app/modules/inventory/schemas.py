from pydantic import BaseModel, Field


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    quantity: float = Field(default=1, ge=0, le=100000)
    unit: str = Field(default="", max_length=30)
    location: str = Field(default="other", max_length=40)
    shelf: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=200)


class InventoryAdjustment(BaseModel):
    delta: float = Field(ge=-100000, le=100000)
