from pydantic import BaseModel, Field


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    quantity: float = Field(default=1, ge=0, le=100000)
    unit: str = Field(default="", max_length=30)
    location: str = Field(default="other", max_length=40)
    shelf: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=200)


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: float | None = Field(default=None, ge=0, le=100000)
    unit: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=40)
    shelf: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=200)


class InventoryAdjustment(BaseModel):
    delta: float = Field(ge=-100000, le=100000)


class InventoryShelfCreate(BaseModel):
    location: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)


class InventoryInboxPlacement(BaseModel):
    location: str = Field(default="", max_length=40)
    shelf: str = Field(default="", max_length=80)


class InventorySuggestionShopping(BaseModel):
    list_id: str = Field(default="shopping", max_length=120)
