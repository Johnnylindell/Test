from __future__ import annotations

from typing import Any, Literal

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


class BudgetSyncSettings(BaseModel):
    source_path: str = Field(default="", max_length=1000)
    auto_sync: bool = False
    poll_seconds: int = Field(default=60, ge=15, le=3600)
    conflict_policy: Literal["review", "source_wins", "app_wins"] = "review"


class BudgetImportRequest(BaseModel):
    payload: dict[str, Any]
    replace: bool = False
    confirm: bool = False
