from pydantic import BaseModel, Field


class ShoppingItemCreate(BaseModel):
    list_id: str = Field(default="shopping", min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=200)
    quantity: float = Field(default=1, gt=0)
    unit: str = Field(default="", max_length=30)
    category: str = Field(default="", max_length=80)
    store: str = Field(default="", max_length=80)


class ShoppingItemUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=80)
    store: str | None = Field(default=None, max_length=80)


class ShoppingCompletion(BaseModel):
    done: bool
