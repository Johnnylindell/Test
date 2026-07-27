from __future__ import annotations

from typing import Any


def first_present(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "ja", "on"}


def as_text(value: Any, *, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]
