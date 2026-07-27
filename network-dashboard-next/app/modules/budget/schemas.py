from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BudgetKind = Literal["income", "expense", "savings"]
BudgetField = Literal["amount", "budgeted", "actual"]


class BudgetEntryCreate(BaseModel):
    sheet: str = Field(min_length=1, max_length=80)
    kind: BudgetKind
    label: str = Field(min_length=1, max_length=120)
    field: BudgetField | None = None
    value: float = Field(ge=0, le=100_000_000)


class BudgetEntryUpdate(BaseModel):
    field: BudgetField
    value: float = Field(ge=0, le=100_000_000)


class BudgetEntryDelete(BaseModel):
    confirm: bool
