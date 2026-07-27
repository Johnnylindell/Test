from __future__ import annotations

from datetime import datetime
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
            now = datetime.utcnow().isoformat()
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
