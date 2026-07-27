from __future__ import annotations

import sqlite3

from app.database.database import Database
from app.modules.banking.importer import parse_statement
from app.modules.banking.repository import BankingRepository


def schema(database: Database) -> None:
    with database.transaction() as connection:
        connection.executescript(
            """
            CREATE TABLE bank_imports(
                id TEXT PRIMARY KEY,filename TEXT,source TEXT,file_hash TEXT,row_count INTEGER,
                imported_count INTEGER,duplicate_count INTEGER,imported_by TEXT,created_at TEXT
            );
            CREATE TABLE bank_transactions(
                id TEXT PRIMARY KEY,fingerprint TEXT UNIQUE,account TEXT,booking_date TEXT,value_date TEXT,
                amount REAL,currency TEXT,description TEXT,counterparty TEXT,reference TEXT,
                transaction_type TEXT,category TEXT,source TEXT,import_id TEXT,created_at TEXT
            );
            CREATE TABLE bank_category_rules(
                id TEXT PRIMARY KEY,pattern TEXT,category TEXT,priority INTEGER,active INTEGER,
                created_at TEXT,updated_at TEXT
            );
            """
        )


def test_parse_nordic_csv_with_decimal_commas() -> None:
    data = (
        "Bokföringsdag;Belopp;Valuta;Mottagare/Betalare;Meddelande;Referens;Konto\n"
        "27.07.2026;-12,50;EUR;K-Market;Matinköp;123;FI001234\n"
        "26.07.2026;1000,00;EUR;Arbetsgivare;Lön;SALARY;FI001234\n"
    ).encode("utf-8")
    result = parse_statement(data, "op.csv")
    assert result["source"] == "csv"
    assert result["summary"]["rows"] == 2
    assert result["summary"]["income"] == 1000.0
    assert result["summary"]["expenses"] == 12.5
    first = result["transactions"][0]
    assert first["booking_date"] == "2026-07-27"
    assert first["amount"] == -12.5
    assert first["category"] == "Mat"
    assert len(first["fingerprint"]) == 64


def test_parse_minimal_camt_statement() -> None:
    data = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
  <BkToCstmrStmt><Stmt><Acct><Id><IBAN>FI001234</IBAN></Id></Acct>
    <Ntry><Amt Ccy="EUR">42.10</Amt><CdtDbtInd>DBIT</CdtDbtInd>
      <BookgDt><Dt>2026-07-27</Dt></BookgDt>
      <NtryDtls><TxDtls><RltdPties><Cdtr><Pty><Nm>Apoteket</Nm></Pty></Cdtr></RltdPties>
      <RmtInf><Ustrd>Medicin</Ustrd></RmtInf><Refs><EndToEndId>REF-1</EndToEndId></Refs></TxDtls></NtryDtls>
    </Ntry>
  </Stmt></BkToCstmrStmt>
</Document>"""
    result = parse_statement(data, "statement.xml")
    assert result["source"] == "camt"
    assert result["summary"]["rows"] == 1
    transaction = result["transactions"][0]
    assert transaction["amount"] == -42.1
    assert transaction["currency"] == "EUR"
    assert transaction["counterparty"] == "Apoteket"
    assert transaction["category"] == "Hälsa"


def test_xml_entities_are_rejected() -> None:
    data = b'<!DOCTYPE foo [<!ENTITY x "boom">]><Document>&x;</Document>'
    try:
        parse_statement(data, "statement.xml")
    except ValueError as exc:
        assert "entiteter" in str(exc)
    else:
        raise AssertionError("XML entities must be rejected")


def test_confirmed_import_is_idempotent(tmp_path) -> None:
    database = Database(tmp_path / "bank.sqlite3")
    schema(database)
    repository = BankingRepository(database)
    parsed = parse_statement(
        b"Booking date,Amount,Currency,Payee,Description\n2026-07-27,-10.00,EUR,Lidl,Food\n",
        "bank.csv",
    )
    first = repository.import_parsed(parsed, "johnny")
    second = repository.import_parsed(parsed, "johnny")
    assert first["imported"] == 1
    assert first["duplicates"] == 0
    assert second["imported"] == 0
    assert second["duplicates"] == 1
    assert database.count("bank_transactions") == 1
    assert database.count("bank_imports") == 2


def test_regex_rules_override_default_categories(tmp_path) -> None:
    database = Database(tmp_path / "rules.sqlite3")
    schema(database)
    repository = BankingRepository(database)
    repository.save_rule("Lidl", "Familjens mat", 10)
    parsed = parse_statement(
        b"Booking date,Amount,Currency,Payee,Description\n2026-07-27,-10.00,EUR,Lidl,Food\n",
        "bank.csv",
    )
    preview = repository.preview(parsed)
    assert preview["transactions"][0]["category"] == "Familjens mat"


def test_banking_migration_uses_unique_fingerprints() -> None:
    connection = sqlite3.connect(":memory:")
    source = open("migrations/0011_banking.py", encoding="utf-8").read()
    assert "fingerprint TEXT NOT NULL UNIQUE" in source
    connection.close()
