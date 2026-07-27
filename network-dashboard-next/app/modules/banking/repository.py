from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BankingRepository:
    REQUIRED = {"bank_imports", "bank_transactions", "bank_category_rules"}

    def __init__(self, database: Database) -> None:
        self.database = database

    def ready(self) -> bool:
        return all(self.database.table_exists(table) for table in self.REQUIRED)

    def rules(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("bank_category_rules"):
            return []
        return self.database.fetch_all(
            "SELECT id,pattern,category,priority,active,created_at,updated_at "
            "FROM bank_category_rules ORDER BY active DESC,priority,id"
        )

    def categorize(self, transaction: dict[str, Any]) -> str:
        haystack = " ".join([
            str(transaction.get("counterparty") or ""),
            str(transaction.get("description") or ""),
            str(transaction.get("transaction_type") or ""),
        ])
        for rule in self.rules():
            if not rule.get("active"):
                continue
            try:
                if re.search(str(rule.get("pattern") or ""), haystack, re.IGNORECASE):
                    return str(rule.get("category") or "Okategoriserat")[:120]
            except re.error:
                continue
        return str(transaction.get("category") or "Okategoriserat")[:120]

    def duplicate_fingerprints(self, fingerprints: list[str]) -> set[str]:
        if not fingerprints or not self.database.table_exists("bank_transactions"):
            return set()
        found: set[str] = set()
        for offset in range(0, len(fingerprints), 500):
            batch = fingerprints[offset: offset + 500]
            placeholders = ",".join("?" for _ in batch)
            rows = self.database.fetch_all(
                f"SELECT fingerprint FROM bank_transactions WHERE fingerprint IN ({placeholders})",
                tuple(batch),
            )
            found.update(str(row["fingerprint"]) for row in rows)
        return found

    def preview(self, parsed: dict[str, Any]) -> dict[str, Any]:
        transactions = [dict(row) for row in parsed.get("transactions") or []]
        existing = self.duplicate_fingerprints([str(row.get("fingerprint") or "") for row in transactions])
        rows = []
        duplicate_count = 0
        for transaction in transactions:
            transaction["category"] = self.categorize(transaction)
            duplicate = transaction.get("fingerprint") in existing
            duplicate_count += int(duplicate)
            rows.append({**transaction, "duplicate": duplicate})
        summary = dict(parsed.get("summary") or {})
        summary.update({
            "duplicates": duplicate_count,
            "new_rows": max(0, len(rows) - duplicate_count),
        })
        return {
            "ok": True,
            "source": parsed.get("source"),
            "filename": parsed.get("filename"),
            "file_hash": parsed.get("file_hash"),
            "summary": summary,
            "transactions": rows[:500],
            "truncated": len(rows) > 500,
            "saved": False,
        }

    def import_parsed(self, parsed: dict[str, Any], actor: str) -> dict[str, Any]:
        if not self.ready():
            raise RuntimeError("Bankimportens databasschema saknas")
        preview = self.preview(parsed)
        import_id = "bank-import-" + secrets.token_hex(8)
        transaction_rows = [row for row in parsed.get("transactions") or [] if isinstance(row, dict)]
        now = _now()
        imported = 0
        duplicates = 0
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO bank_imports(id,filename,source,file_hash,row_count,imported_count,duplicate_count,imported_by,created_at) "
                "VALUES(?,?,?,?,?,0,0,?,?)",
                (
                    import_id,
                    str(parsed.get("filename") or "statement")[:240],
                    str(parsed.get("source") or "unknown")[:40],
                    str(parsed.get("file_hash") or "")[:64],
                    len(transaction_rows),
                    actor[:80],
                    now,
                ),
            )
            for row in transaction_rows:
                category = self.categorize(row)
                transaction_id = "bank-tx-" + secrets.token_hex(8)
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO bank_transactions("
                    "id,fingerprint,account,booking_date,value_date,amount,currency,description,counterparty,reference,"
                    "transaction_type,category,source,import_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        transaction_id,
                        str(row.get("fingerprint") or "")[:64],
                        str(row.get("account") or "")[:120],
                        str(row.get("booking_date") or "")[:10],
                        str(row.get("value_date") or "")[:10],
                        float(row.get("amount") or 0),
                        str(row.get("currency") or "EUR")[:10],
                        str(row.get("description") or "")[:1000],
                        str(row.get("counterparty") or "")[:300],
                        str(row.get("reference") or "")[:200],
                        str(row.get("transaction_type") or "")[:120],
                        category,
                        str(parsed.get("source") or "unknown")[:40],
                        import_id,
                        now,
                    ),
                )
                if cursor.rowcount == 1:
                    imported += 1
                else:
                    duplicates += 1
            connection.execute(
                "UPDATE bank_imports SET imported_count=?,duplicate_count=? WHERE id=?",
                (imported, duplicates, import_id),
            )
        return {
            "ok": True,
            "import_id": import_id,
            "rows": len(transaction_rows),
            "imported": imported,
            "duplicates": duplicates,
            "summary": preview["summary"],
        }

    def overview(self, limit: int = 100) -> dict[str, Any]:
        if not self.ready():
            return {
                "ok": False,
                "ready": False,
                "transactions": [],
                "imports": [],
                "rules": [],
                "totals": {},
            }
        transactions = self.database.fetch_all(
            "SELECT id,account,booking_date,value_date,amount,currency,description,counterparty,reference,"
            "transaction_type,category,source,import_id,created_at FROM bank_transactions "
            "ORDER BY booking_date DESC,id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        )
        imports = self.database.fetch_all(
            "SELECT id,filename,source,row_count,imported_count,duplicate_count,imported_by,created_at "
            "FROM bank_imports ORDER BY created_at DESC LIMIT 30"
        )
        totals = self.database.fetch_one(
            "SELECT COUNT(*) AS transactions,"
            "COALESCE(SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),0) AS income,"
            "COALESCE(SUM(CASE WHEN amount<0 THEN -amount ELSE 0 END),0) AS expenses,"
            "MIN(booking_date) AS date_from,MAX(booking_date) AS date_to FROM bank_transactions"
        ) or {}
        categories = self.database.fetch_all(
            "SELECT category,COUNT(*) AS transactions,"
            "COALESCE(SUM(CASE WHEN amount<0 THEN -amount ELSE 0 END),0) AS expenses "
            "FROM bank_transactions GROUP BY category ORDER BY expenses DESC,category"
        )
        return {
            "ok": True,
            "ready": True,
            "transactions": transactions,
            "imports": imports,
            "rules": self.rules(),
            "totals": totals,
            "categories": categories,
        }

    def save_rule(self, pattern: str, category: str, priority: int, active: bool = True) -> str:
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise ValueError("Kategoriregeln är inte giltig regex") from exc
        rule_id = "bank-rule-" + secrets.token_hex(8)
        now = _now()
        self.database.execute(
            "INSERT INTO bank_category_rules(id,pattern,category,priority,active,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (rule_id, pattern[:300], category[:120], max(0, min(priority, 10_000)), 1 if active else 0, now, now),
        )
        return rule_id

    def delete_rule(self, rule_id: str) -> bool:
        before = self.database.count("bank_category_rules", "id=?", (rule_id,))
        self.database.execute("DELETE FROM bank_category_rules WHERE id=?", (rule_id,))
        return before == 1
