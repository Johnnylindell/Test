from pydantic import BaseModel, Field


class MealSet(BaseModel):
    week_start: str = Field(min_length=10, max_length=10)
    day: str = Field(min_length=2, max_length=12)
    title: str = Field(min_length=1, max_length=160)
    meal_id: str = Field(default="", max_length=160)
    url: str = Field(default="", max_length=1200)
    source: str = Field(default="Manuellt", max_length=120)
