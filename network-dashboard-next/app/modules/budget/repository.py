from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database.database import Database

_LAYOUT = {
    "income": {"label": 2, "amount": 3},
    "expense": {"label": 5, "budgeted": 6, "actual": 7},
    "savings": {"label": 9, "amount": 10},
}
_SKIP = {
    "personal budget", "summary", "item", "amount", "due date", "date", "kategori",
    "budgeterat", "faktiska räkningar", "type", "percentage of income spent",
    "monthly income", "monthly expenses", "monthly savings", "savings", "income", "expenses",
}


def _number(value: Any) -> float:
    try:
        return float(str(value or "0").replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BudgetRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def _require_schema(self) -> None:
        if not {"budget_sheets", "budget_cells"} <= {
            name for name in ("budget_sheets", "budget_cells") if self.database.table_exists(name)
        }:
            raise RuntimeError("Budgettabeller saknas; kör databasmigreringen först")

    def sheets(self) -> list[dict[str, Any]]:
        self._require_schema()
        return self.database.fetch_all(
            "SELECT id,name,kind,sort_order FROM budget_sheets WHERE kind='month' ORDER BY sort_order,id"
        )

    def _selected_sheet(self, sheet_name: str = "") -> dict[str, Any] | None:
        sheets = self.sheets()
        if not sheets:
            return None
        selected = next((row for row in sheets if row["name"] == sheet_name), None)
        if selected:
            return selected
        month_names = {
            1: ("januari", "january"), 2: ("februari", "february"), 3: ("mars",),
            4: ("april",), 5: ("maj", "may"), 6: ("juni", "june"), 7: ("juli", "july"),
            8: ("augusti", "august"), 9: ("september",), 10: ("oktober", "october"),
            11: ("november",), 12: ("december",),
        }
        return next(
            (row for row in sheets if any(name in row["name"].lower() for name in month_names[datetime.now().month])),
            sheets[-1],
        )

    def overview(self, sheet_name: str = "") -> dict[str, Any]:
        selected = self._selected_sheet(sheet_name)
        sheets = self.sheets()
        if not selected:
            return {"configured": False, "sheets": [], "income": [], "expenses": [], "savings": [], "totals": {}}
        rows = self.database.fetch_all(
            "SELECT row_num,col_num,value FROM budget_cells WHERE sheet_id=? ORDER BY row_num,col_num",
            (selected["id"],),
        )
        cells = {(int(row["row_num"]), int(row["col_num"])): str(row["value"] or "") for row in rows}
        income: list[dict[str, Any]] = []
        expenses: list[dict[str, Any]] = []
        savings: list[dict[str, Any]] = []
        for row_num in sorted({row for row, _ in cells}):
            income_label = cells.get((row_num, 2), "").strip()
            expense_label = cells.get((row_num, 5), "").strip()
            savings_label = cells.get((row_num, 9), "").strip()
            if income_label and income_label.lower() not in _SKIP and not income_label.lower().startswith("total"):
                income.append({"id": f"{selected['id']}:income:{row_num}", "row": row_num, "category": income_label[:120], "amount": round(_number(cells.get((row_num, 3))), 2)})
            if expense_label and expense_label.lower() not in _SKIP and not expense_label.lower().startswith("total"):
                expenses.append({"id": f"{selected['id']}:expense:{row_num}", "row": row_num, "category": expense_label[:120], "budgeted": round(_number(cells.get((row_num, 6))), 2), "actual": round(_number(cells.get((row_num, 7))), 2)})
            if savings_label and savings_label != "[Date]" and savings_label.lower() not in _SKIP and not savings_label.lower().startswith("total"):
                savings.append({"id": f"{selected['id']}:savings:{row_num}", "row": row_num, "category": savings_label[:120], "amount": round(_number(cells.get((row_num, 10))), 2)})
        total_income = round(sum(row["amount"] for row in income), 2)
        budgeted = round(sum(row["budgeted"] for row in expenses), 2)
        actual = round(sum(row["actual"] for row in expenses), 2)
        saved = round(sum(row["amount"] for row in savings), 2)
        return {
            "configured": True,
            "current": selected["name"],
            "sheets": [row["name"] for row in sheets],
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "totals": {
                "income": total_income,
                "expenses_budgeted": budgeted,
                "expenses_actual": actual,
                "savings": saved,
                "balance_budgeted": round(total_income - budgeted - saved, 2),
                "balance_actual": round(total_income - actual - saved, 2),
                "spent_pct_actual": round(actual / total_income * 100, 1) if total_income else 0.0,
            },
        }

    def year_summary(self) -> dict[str, Any]:
        months = []
        categories: dict[str, float] = {}
        totals = {"income": 0.0, "expenses": 0.0, "savings": 0.0, "balance": 0.0}
        for sheet in self.sheets():
            view = self.overview(sheet["name"])
            month_totals = view.get("totals") or {}
            income = float(month_totals.get("income") or 0)
            actual = float(month_totals.get("expenses_actual") or 0)
            budgeted = float(month_totals.get("expenses_budgeted") or 0)
            expenses = actual if actual else budgeted
            savings = float(month_totals.get("savings") or 0)
            balance = income - expenses - savings
            months.append({
                "sheet": sheet["name"],
                "income": round(income, 2),
                "expenses": round(expenses, 2),
                "savings": round(savings, 2),
                "balance": round(balance, 2),
            })
            totals["income"] += income
            totals["expenses"] += expenses
            totals["savings"] += savings
            totals["balance"] += balance
            for expense in view.get("expenses") or []:
                amount = float(expense.get("actual") or 0) or float(expense.get("budgeted") or 0)
                label = str(expense.get("category") or "Övrigt")
                categories[label] = categories.get(label, 0.0) + amount
        return {
            "ok": True,
            "months": months,
            "categories": [
                {"category": key, "amount": round(value, 2)}
                for key, value in sorted(categories.items(), key=lambda item: item[1], reverse=True)
            ],
            "totals": {key: round(value, 2) for key, value in totals.items()},
        }

    def export_payload(self) -> dict[str, Any]:
        self._require_schema()
        sheets = self.database.fetch_all(
            "SELECT id,name,kind,sort_order,max_row,max_col FROM budget_sheets ORDER BY sort_order,id"
        )
        for sheet in sheets:
            sheet["cells"] = self.database.fetch_all(
                "SELECT row_num,col_num,value,updated_at FROM budget_cells WHERE sheet_id=? ORDER BY row_num,col_num",
                (sheet["id"],),
            )
        return {"format": "network-dashboard-budget-v1", "exported_at": _now(), "sheets": sheets}

    def import_payload(self, payload: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
        if payload.get("format") != "network-dashboard-budget-v1" or not isinstance(payload.get("sheets"), list):
            raise ValueError("Ogiltigt budgetformat")
        changed = 0
        with self.database.transaction() as connection:
            if replace:
                connection.execute("DELETE FROM budget_cells")
                connection.execute("DELETE FROM budget_sheets")
            for order, sheet in enumerate(payload["sheets"][:100]):
                if not isinstance(sheet, dict):
                    continue
                name = str(sheet.get("name") or "").strip()[:80]
                if not name:
                    continue
                kind = str(sheet.get("kind") or "month")[:30]
                row = connection.execute("SELECT id FROM budget_sheets WHERE name=?", (name,)).fetchone()
                if row:
                    sheet_id = int(row[0])
                else:
                    cursor = connection.execute(
                        "INSERT INTO budget_sheets(name,kind,sort_order,max_row,max_col) VALUES(?,?,?,?,?)",
                        (name, kind, int(sheet.get("sort_order") or order), int(sheet.get("max_row") or 40), int(sheet.get("max_col") or 12)),
                    )
                    sheet_id = int(cursor.lastrowid)
                for cell in list(sheet.get("cells") or [])[:10000]:
                    if not isinstance(cell, dict):
                        continue
                    row_num = int(cell.get("row_num") or 0)
                    col_num = int(cell.get("col_num") or 0)
                    if not 1 <= row_num <= 10000 or not 1 <= col_num <= 1000:
                        continue
                    connection.execute(
                        "INSERT INTO budget_cells(sheet_id,row_num,col_num,value,updated_at) VALUES(?,?,?,?,?) "
                        "ON CONFLICT(sheet_id,row_num,col_num) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                        (sheet_id, row_num, col_num, str(cell.get("value") or "")[:4000], _now()),
                    )
                    changed += 1
        self._sync_event("import", "ok", "Budgetdata importerades", changed)
        self.database.execute("UPDATE budget_sync_state SET last_import_at=?,last_error='',updated_at=? WHERE id=1", (_now(), _now()))
        return {"ok": True, "changed_cells": changed, "sheets": len(payload["sheets"])}

    def sync_status(self) -> dict[str, Any]:
        if not self.database.table_exists("budget_sync_state"):
            return {"ok": True, "mode": "migration_required", "recent_events": []}
        state = self.database.fetch_one("SELECT * FROM budget_sync_state WHERE id=1") or {}
        events = self.database.fetch_all(
            "SELECT created_at,direction,status,message,changed_cells FROM budget_sync_events ORDER BY id DESC LIMIT 8"
        )
        return {
            "ok": True,
            "mode": "configured" if state.get("source_path") else "not_configured",
            "source_path": state.get("source_path") or "",
            "auto_sync": bool(state.get("auto_sync")),
            "poll_seconds": int(state.get("poll_seconds") or 60),
            "conflict_policy": state.get("conflict_policy") or "review",
            "last_import_at": state.get("last_import_at") or "",
            "last_export_at": state.get("last_export_at") or "",
            "last_error": state.get("last_error") or "",
            "recent_events": events,
            "message": "Next använder säker import/export. Direkt skrivning till original-Excel är inte aktiverad.",
        }

    def update_sync_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        policy = str(data.get("conflict_policy") or "review")
        if policy not in {"review", "source_wins", "app_wins"}:
            raise ValueError("Ogiltig konfliktpolicy")
        self.database.execute(
            "INSERT INTO budget_sync_state(id,source_path,auto_sync,poll_seconds,conflict_policy,updated_at) "
            "VALUES(1,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_path=excluded.source_path," 
            "auto_sync=excluded.auto_sync,poll_seconds=excluded.poll_seconds," 
            "conflict_policy=excluded.conflict_policy,updated_at=excluded.updated_at",
            (
                str(data.get("source_path") or "")[:1000],
                1 if data.get("auto_sync") else 0,
                max(15, min(3600, int(data.get("poll_seconds") or 60))),
                policy,
                _now(),
            ),
        )
        self._sync_event("settings", "ok", "Budgetsynkinställningar uppdaterades", 0)
        return self.sync_status()

    def _sync_event(self, direction: str, status: str, message: str, changed_cells: int) -> None:
        if not self.database.table_exists("budget_sync_events"):
            return
        self.database.execute(
            "INSERT INTO budget_sync_events(created_at,direction,status,message,changed_cells) VALUES(?,?,?,?,?)",
            (_now(), direction[:40], status[:40], message[:500], int(changed_cells)),
        )

    def add_entry(self, data: dict[str, Any]) -> None:
        self._require_schema()
        layout = _LAYOUT[data["kind"]]
        field = data.get("field") or ("actual" if data["kind"] == "expense" else "amount")
        if field not in layout or field == "label":
            raise ValueError("Ogiltigt budgetfält")
        with self.database.transaction() as connection:
            sheet = connection.execute("SELECT id FROM budget_sheets WHERE name=? AND kind='month'", (data["sheet"],)).fetchone()
            if not sheet:
                raise ValueError("Budgetmånaden finns inte")
            sheet_id = int(sheet[0])
            duplicate = connection.execute("SELECT 1 FROM budget_cells WHERE sheet_id=? AND col_num=? AND TRIM(value)=?", (sheet_id, layout["label"], data["label"])).fetchone()
            if duplicate:
                raise ValueError("Kategorin finns redan i månaden")
            row_num = max(18, int(connection.execute("SELECT COALESCE(MAX(row_num),17) FROM budget_cells WHERE sheet_id=? AND col_num=?", (sheet_id, layout["label"])).fetchone()[0]) + 1)
            now = _now()
            connection.execute("INSERT INTO budget_cells(sheet_id,row_num,col_num,value,updated_at) VALUES(?,?,?,?,?)", (sheet_id, row_num, layout["label"], data["label"], now))
            connection.execute("INSERT INTO budget_cells(sheet_id,row_num,col_num,value,updated_at) VALUES(?,?,?,?,?)", (sheet_id, row_num, layout[field], str(data["value"]), now))

    def update_entry(self, entry_id: str, field: str, value: float) -> None:
        sheet_id, kind, row_text = entry_id.split(":", 2)
        layout = _LAYOUT[kind]
        if field not in layout or field == "label":
            raise ValueError("Ogiltigt budgetfält")
        self.database.execute(
            "INSERT INTO budget_cells(sheet_id,row_num,col_num,value,updated_at) VALUES(?,?,?,?,datetime('now')) ON CONFLICT(sheet_id,row_num,col_num) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (int(sheet_id), int(row_text), layout[field], str(value)),
        )

    def delete_entry(self, entry_id: str) -> None:
        sheet_id, kind, row_text = entry_id.split(":", 2)
        columns = tuple(_LAYOUT[kind].values())
        placeholders = ",".join("?" for _ in columns)
        self.database.execute(
            f"DELETE FROM budget_cells WHERE sheet_id=? AND row_num=? AND col_num IN ({placeholders})",
            (int(sheet_id), int(row_text), *columns),
        )
