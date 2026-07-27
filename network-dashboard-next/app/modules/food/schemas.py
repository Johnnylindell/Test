from pydantic import BaseModel, Field


class MealSet(BaseModel):
    week_start: str = Field(min_length=10, max_length=10)
    day: str = Field(min_length=2, max_length=12)
    title: str = Field(min_length=1, max_length=160)
    meal_id: str = Field(default="", max_length=160)
    url: str = Field(default="", max_length=1200)
    source: str = Field(default="Manuellt", max_length=120)


class RecipeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_url: str = Field(default="", max_length=1200)
    source_name: str = Field(default="Manuellt", max_length=120)
    image_url: str = Field(default="", max_length=1200)
    ingredients: list[str] = Field(default_factory=list, max_length=200)
    steps: list[str] = Field(default_factory=list, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=30)
    servings: str = Field(default="", max_length=80)
    favorite: bool = True


class RecipeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=1200)
    source_name: str | None = Field(default=None, max_length=120)
    image_url: str | None = Field(default=None, max_length=1200)
    ingredients: list[str] | None = Field(default=None, max_length=200)
    steps: list[str] | None = Field(default=None, max_length=100)
    tags: list[str] | None = Field(default=None, max_length=30)
    servings: str | None = Field(default=None, max_length=80)
    favorite: bool | None = None


class IngredientsToShopping(BaseModel):
    ingredients: list[str] = Field(default_factory=list, min_length=1, max_length=200)
    list_id: str = Field(default="shopping", max_length=120)
    source: str = Field(default="Recept", max_length=120)
