from __future__ import annotations

import sqlite3


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
        CREATE INDEX IF NOT EXISTS idx_bank_imports_created
            ON bank_imports(created_at DESC);

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
        CREATE INDEX IF NOT EXISTS idx_bank_transactions_booking
            ON bank_transactions(booking_date DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_bank_transactions_category
            ON bank_transactions(category, booking_date DESC);

        CREATE TABLE IF NOT EXISTS bank_category_rules(
            id TEXT PRIMARY KEY,
            pattern TEXT NOT NULL,
            category TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bank_category_rules_priority
            ON bank_category_rules(active DESC, priority, id);
        """
    )
