from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from app.database.schema_helpers import ensure_columns, ensure_index, table_columns


def _copy_first(
    connection: sqlite3.Connection,
    table: str,
    target: str,
    candidates: Iterable[str],
) -> None:
    columns = table_columns(connection, table)
    if target not in columns:
        return
    for source in candidates:
        if source not in columns or source == target:
            continue
        connection.execute(
            f'UPDATE "{table}" SET "{target}"="{source}" '
            f'WHERE ("{target}" IS NULL OR TRIM(CAST("{target}" AS TEXT))="") '
            f'AND "{source}" IS NOT NULL'
        )
        return


def _copy_number(
    connection: sqlite3.Connection,
    table: str,
    target: str,
    candidates: Iterable[str],
) -> None:
    columns = table_columns(connection, table)
    if target not in columns:
        return
    for source in candidates:
        if source not in columns or source == target:
            continue
        connection.execute(
            f'UPDATE "{table}" SET "{target}"="{source}" '
            f'WHERE COALESCE("{target}",0)=0 AND "{source}" IS NOT NULL'
        )
        return


def _fill_unique(connection: sqlite3.Connection, table: str, column: str, prefix: str) -> None:
    connection.execute(
        f'UPDATE "{table}" SET "{column}"=? || rowid '
        f'WHERE "{column}" IS NULL OR TRIM(CAST("{column}" AS TEXT))=""',
        (prefix,),
    )
    duplicates = connection.execute(
        f'SELECT "{column}" FROM "{table}" GROUP BY "{column}" HAVING COUNT(*) > 1'
    ).fetchall()
    for (value,) in duplicates:
        rows = connection.execute(
            f'SELECT rowid FROM "{table}" WHERE "{column}"=? ORDER BY rowid',
            (value,),
        ).fetchall()
        for (rowid,) in rows[1:]:
            connection.execute(
                f'UPDATE "{table}" SET "{column}"=? WHERE rowid=?',
                (f"{value}-{prefix}{rowid}", rowid),
            )


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS bank_imports(
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            source TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            imported_count INTEGER NOT NULL DEFAULT 0,
            duplicate_count INTEGER NOT NULL DEFAULT 0,
            imported_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bank_transactions(
            id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE,
            account TEXT NOT NULL DEFAULT '',
            booking_date TEXT NOT NULL,
            value_date TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'EUR',
            description TEXT NOT NULL DEFAULT '',
            counterparty TEXT NOT NULL DEFAULT '',
            reference TEXT NOT NULL DEFAULT '',
            transaction_type TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'Okategoriserat',
            source TEXT NOT NULL,
            import_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(import_id) REFERENCES bank_imports(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS bank_category_rules(
            id TEXT PRIMARY KEY,
            pattern TEXT NOT NULL,
            category TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )

    ensure_columns(
        connection,
        "bank_imports",
        (
            ("id", "TEXT NOT NULL DEFAULT ''"),
            ("filename", "TEXT NOT NULL DEFAULT ''"),
            ("source", "TEXT NOT NULL DEFAULT 'legacy'"),
            ("file_hash", "TEXT NOT NULL DEFAULT ''"),
            ("row_count", "INTEGER NOT NULL DEFAULT 0"),
            ("imported_count", "INTEGER NOT NULL DEFAULT 0"),
            ("duplicate_count", "INTEGER NOT NULL DEFAULT 0"),
            ("imported_by", "TEXT NOT NULL DEFAULT ''"),
            ("created_at", "TEXT NOT NULL DEFAULT ''"),
        ),
    )
    ensure_columns(
        connection,
        "bank_transactions",
        (
            ("id", "TEXT NOT NULL DEFAULT ''"),
            ("fingerprint", "TEXT NOT NULL DEFAULT ''"),
            ("account", "TEXT NOT NULL DEFAULT ''"),
            ("booking_date", "TEXT NOT NULL DEFAULT ''"),
            ("value_date", "TEXT NOT NULL DEFAULT ''"),
            ("amount", "REAL NOT NULL DEFAULT 0"),
            ("currency", "TEXT NOT NULL DEFAULT 'EUR'"),
            ("description", "TEXT NOT NULL DEFAULT ''"),
            ("counterparty", "TEXT NOT NULL DEFAULT ''"),
            ("reference", "TEXT NOT NULL DEFAULT ''"),
            ("transaction_type", "TEXT NOT NULL DEFAULT ''"),
            ("category", "TEXT NOT NULL DEFAULT 'Okategoriserat'"),
            ("source", "TEXT NOT NULL DEFAULT 'legacy'"),
            ("import_id", "TEXT NOT NULL DEFAULT ''"),
            ("created_at", "TEXT NOT NULL DEFAULT ''"),
        ),
    )
    ensure_columns(
        connection,
        "bank_category_rules",
        (
            ("id", "TEXT NOT NULL DEFAULT ''"),
            ("pattern", "TEXT NOT NULL DEFAULT ''"),
            ("category", "TEXT NOT NULL DEFAULT 'Okategoriserat'"),
            ("priority", "INTEGER NOT NULL DEFAULT 100"),
            ("active", "INTEGER NOT NULL DEFAULT 1"),
            ("created_at", "TEXT NOT NULL DEFAULT ''"),
            ("updated_at", "TEXT NOT NULL DEFAULT ''"),
        ),
    )

    _copy_first(connection, "bank_transactions", "booking_date", ("date", "transaction_date", "booked_at"))
    _copy_first(connection, "bank_transactions", "value_date", ("valueDate", "valuta_date"))
    _copy_number(connection, "bank_transactions", "amount", ("value", "sum", "transaction_amount"))
    _copy_first(connection, "bank_transactions", "account", ("account_name", "account_id", "iban"))
    _copy_first(connection, "bank_transactions", "description", ("text", "message", "details", "name"))
    _copy_first(connection, "bank_transactions", "counterparty", ("payee", "recipient", "payer"))
    _copy_first(connection, "bank_transactions", "reference", ("reference_number", "ref"))
    _copy_first(connection, "bank_transactions", "transaction_type", ("type", "kind"))
    _copy_first(connection, "bank_transactions", "created_at", ("imported_at", "timestamp"))
    connection.execute(
        "UPDATE bank_transactions SET value_date=booking_date WHERE value_date='' AND booking_date<>''"
    )
    connection.execute(
        "UPDATE bank_transactions SET created_at=datetime('now') WHERE created_at=''"
    )
    connection.execute(
        "UPDATE bank_transactions SET source='legacy' WHERE source=''"
    )
    connection.execute(
        "UPDATE bank_transactions SET category='Okategoriserat' WHERE category=''"
    )

    _fill_unique(connection, "bank_imports", "id", "legacy-bank-import-")
    _fill_unique(connection, "bank_transactions", "id", "legacy-bank-tx-")
    _fill_unique(connection, "bank_transactions", "fingerprint", "legacy-bank-fingerprint-")
    _fill_unique(connection, "bank_category_rules", "id", "legacy-bank-rule-")

    transaction_count = connection.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0]
    if transaction_count:
        connection.execute(
            "INSERT OR IGNORE INTO bank_imports("
            "id,filename,source,file_hash,row_count,imported_count,duplicate_count,imported_by,created_at"
            ") VALUES('legacy-bank-import','legacy-database','legacy','legacy-database',?,?,0,'migration',datetime('now'))",
            (transaction_count, transaction_count),
        )
        connection.execute(
            "UPDATE bank_transactions SET import_id='legacy-bank-import' WHERE import_id=''"
        )

    ensure_index(
        connection,
        "ux_bank_transactions_fingerprint",
        "CREATE UNIQUE INDEX ux_bank_transactions_fingerprint ON bank_transactions(fingerprint)",
    )
    ensure_index(
        connection,
        "idx_bank_imports_created",
        "CREATE INDEX idx_bank_imports_created ON bank_imports(created_at DESC)",
    )
    ensure_index(
        connection,
        "idx_bank_transactions_booking",
        "CREATE INDEX idx_bank_transactions_booking ON bank_transactions(booking_date DESC,id DESC)",
    )
    ensure_index(
        connection,
        "idx_bank_transactions_category",
        "CREATE INDEX idx_bank_transactions_category ON bank_transactions(category,booking_date DESC)",
    )
    ensure_index(
        connection,
        "idx_bank_category_rules_priority",
        "CREATE INDEX idx_bank_category_rules_priority ON bank_category_rules(active DESC,priority,id)",
    )
