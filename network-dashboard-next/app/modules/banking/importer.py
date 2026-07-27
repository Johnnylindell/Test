from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree

_MAX_BYTES = 10 * 1024 * 1024
_MAX_ROWS = 20_000

_HEADER_ALIASES = {
    "booking_date": {
        "booking date", "date", "bokföringsdag", "bokforingsdag", "kirjauspäivä", "kirjauspaiva",
        "transaction date", "transaktionsdag", "tapahtumapäivä", "tapahtumapaiva",
    },
    "value_date": {"value date", "valutadag", "arvopäivä", "arvopaiva"},
    "amount": {"amount", "belopp", "määrä", "maara", "sum", "summa"},
    "currency": {"currency", "valuta", "valuutta"},
    "description": {
        "description", "beskrivning", "message", "meddelande", "viesti", "details", "detaljer",
        "additional information", "lisätiedot", "lisatiedot",
    },
    "counterparty": {
        "counterparty", "payee", "payer", "mottagare", "betalare", "saaja", "maksaja",
        "saaja/maksaja", "mottagare/betalare", "name", "namn", "nimi",
    },
    "reference": {"reference", "referens", "viite", "reference number", "referensnummer"},
    "transaction_type": {
        "transaction type", "transaktionstyp", "tapahtumalaji", "type", "typ", "laji",
    },
    "account": {"account", "konto", "tili", "account number", "kontonummer", "tilinumero"},
    "debit": {"debit", "debitering", "debet", "veloitus"},
    "credit": {"credit", "kreditering", "kredit", "hyvitys"},
}

_DEFAULT_CATEGORY_RULES = [
    ("Mat", ("k-market", "s-market", "prisma", "lidl", "market", "supermarket", "grocery")),
    ("Transport", ("shell", "neste", "st1", "fuel", "bensin", "diesel", "taxi")),
    ("Boende", ("hyra", "rent", "mortgage", "bolån", "bolan", "electricity", "elräkning", "elrakning")),
    ("Kommunikation", ("telia", "elisa", "telefon", "internet", "broadband", "bredband")),
    ("Hälsa", ("apotek", "pharmacy", "läkare", "lakare", "doctor", "dental", "tandläkare")),
    ("Försäkringar", ("försäkring", "forsakring", "insurance")),
    ("Barn", ("dagis", "förskola", "forskola", "school", "skola", "hobby")),
]


def _normalize_header(value: Any) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    return text.replace("_", " ").replace("-", " ")


def _field_map(headers: list[str]) -> dict[str, str]:
    normalized = {_normalize_header(header): header for header in headers if header}
    result: dict[str, str] = {}
    for target, aliases in _HEADER_ALIASES.items():
        match = next((normalized[alias] for alias in aliases if alias in normalized), None)
        if match:
            result[target] = match
    return result


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Kontoutdragets teckenkodning kunde inte läsas")


def _date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidates = [text[:10], text]
    for candidate in candidates:
        try:
            return date.fromisoformat(candidate).isoformat()
        except ValueError:
            pass
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Ogiltigt datum: {text[:40]}")


def _amount(value: Any) -> Decimal:
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return Decimal("0")
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = re.sub(r"[^0-9,.-]", "", text)
    if text.count(",") == 1 and text.count(".") >= 1:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif text.count(",") == 1:
        text = text.replace(",", ".")
    elif text.count(",") > 1:
        text = text.replace(",", "")
    try:
        result = Decimal(text or "0")
    except InvalidOperation as exc:
        raise ValueError(f"Ogiltigt belopp: {str(value)[:40]}") from exc
    return -result if negative else result


def _text(*values: Any, limit: int = 1000) -> str:
    parts = [" ".join(str(value or "").strip().split()) for value in values]
    return " · ".join(part for part in parts if part)[:limit]


def _category(transaction: dict[str, Any], rules: list[tuple[str, tuple[str, ...]]] | None = None) -> str:
    haystack = _text(
        transaction.get("counterparty"),
        transaction.get("description"),
        transaction.get("transaction_type"),
        limit=2000,
    ).casefold()
    for category, patterns in rules or _DEFAULT_CATEGORY_RULES:
        if any(pattern.casefold() in haystack for pattern in patterns):
            return category
    return "Okategoriserat"


def _fingerprint(transaction: dict[str, Any]) -> str:
    normalized = "|".join([
        str(transaction.get("account") or "").casefold(),
        str(transaction.get("booking_date") or ""),
        f"{Decimal(str(transaction.get('amount') or 0)):.2f}",
        str(transaction.get("currency") or "EUR").upper(),
        str(transaction.get("reference") or "").casefold(),
        str(transaction.get("counterparty") or "").casefold(),
        str(transaction.get("description") or "").casefold(),
    ])
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _finalize(transaction: dict[str, Any]) -> dict[str, Any]:
    booking_date = _date(transaction.get("booking_date"))
    if not booking_date:
        raise ValueError("Transaktionen saknar bokföringsdatum")
    amount = Decimal(str(transaction.get("amount") or "0"))
    result = {
        "account": _text(transaction.get("account"), limit=120),
        "booking_date": booking_date,
        "value_date": _date(transaction.get("value_date")) or booking_date,
        "amount": float(amount.quantize(Decimal("0.01"))),
        "currency": (_text(transaction.get("currency"), limit=10) or "EUR").upper(),
        "description": _text(transaction.get("description"), limit=1000),
        "counterparty": _text(transaction.get("counterparty"), limit=300),
        "reference": _text(transaction.get("reference"), limit=200),
        "transaction_type": _text(transaction.get("transaction_type"), limit=120),
    }
    result["category"] = _category(result)
    result["fingerprint"] = _fingerprint(result)
    return result


def parse_csv(data: bytes) -> list[dict[str, Any]]:
    text = _decode(data)
    sample = text[:16_384]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV-filen saknar rubrikrad")
    fields = _field_map([str(header or "") for header in reader.fieldnames])
    if "booking_date" not in fields or ("amount" not in fields and not ({"debit", "credit"} & fields.keys())):
        raise ValueError("CSV-filen saknar datum- eller beloppskolumn")
    transactions = []
    for index, row in enumerate(reader, start=2):
        if len(transactions) >= _MAX_ROWS:
            raise ValueError("Kontoutdraget innehåller för många transaktioner")
        if not any(str(value or "").strip() for value in row.values()):
            continue
        try:
            if "amount" in fields:
                amount = _amount(row.get(fields["amount"]))
            else:
                credit = _amount(row.get(fields.get("credit", "")))
                debit = _amount(row.get(fields.get("debit", "")))
                amount = credit - abs(debit)
            transactions.append(_finalize({
                "booking_date": row.get(fields["booking_date"]),
                "value_date": row.get(fields.get("value_date", "")),
                "amount": amount,
                "currency": row.get(fields.get("currency", "")) or "EUR",
                "description": row.get(fields.get("description", "")),
                "counterparty": row.get(fields.get("counterparty", "")),
                "reference": row.get(fields.get("reference", "")),
                "transaction_type": row.get(fields.get("transaction_type", "")),
                "account": row.get(fields.get("account", "")),
            }))
        except ValueError as exc:
            raise ValueError(f"Rad {index}: {exc}") from exc
    return transactions


def _local_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _find_text(element: ElementTree.Element, names: tuple[str, ...]) -> str:
    wanted = set(names)
    for child in element.iter():
        if _local_name(child) in wanted and child.text:
            return child.text.strip()
    return ""


def parse_camt(data: bytes) -> list[dict[str, Any]]:
    head = data[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise ValueError("XML med externa entiteter stöds inte")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError("CAMT-filen är inte giltig XML") from exc
    account = _find_text(root, ("IBAN", "Id"))
    transactions = []
    for entry in (element for element in root.iter() if _local_name(element) == "Ntry"):
        if len(transactions) >= _MAX_ROWS:
            raise ValueError("Kontoutdraget innehåller för många transaktioner")
        amount_element = next((child for child in entry.iter() if _local_name(child) == "Amt" and child.text), None)
        if amount_element is None:
            continue
        amount = _amount(amount_element.text)
        direction = _find_text(entry, ("CdtDbtInd",))
        if direction == "DBIT":
            amount = -abs(amount)
        elif direction == "CRDT":
            amount = abs(amount)
        booking_date = _find_text(entry, ("BookgDt", "Dt", "DtTm"))
        value_date = _find_text(entry, ("ValDt",))
        counterparty = _find_text(entry, ("Nm",))
        reference = _find_text(entry, ("EndToEndId", "CdtrRef", "AcctSvcrRef", "UETR"))
        description = _text(
            _find_text(entry, ("Ustrd",)),
            _find_text(entry, ("AddtlNtryInf",)),
            limit=1000,
        )
        transactions.append(_finalize({
            "account": account,
            "booking_date": booking_date[:10],
            "value_date": value_date[:10],
            "amount": amount,
            "currency": amount_element.attrib.get("Ccy", "EUR"),
            "description": description,
            "counterparty": counterparty,
            "reference": reference,
            "transaction_type": _find_text(entry, ("Prtry", "Cd")),
        }))
    if not transactions:
        raise ValueError("CAMT-filen innehåller inga läsbara transaktioner")
    return transactions


def parse_statement(data: bytes, filename: str = "") -> dict[str, Any]:
    if not data:
        raise ValueError("Kontoutdraget är tomt")
    if len(data) > _MAX_BYTES:
        raise ValueError("Kontoutdraget är för stort")
    stripped = data.lstrip()
    source = "camt" if stripped.startswith(b"<") or filename.casefold().endswith(".xml") else "csv"
    transactions = parse_camt(data) if source == "camt" else parse_csv(data)
    file_hash = hashlib.sha256(data).hexdigest()
    return {
        "source": source,
        "filename": str(filename or f"statement.{source}")[:240],
        "file_hash": file_hash,
        "transactions": transactions,
        "summary": {
            "rows": len(transactions),
            "income": round(sum(max(0.0, row["amount"]) for row in transactions), 2),
            "expenses": round(sum(abs(min(0.0, row["amount"])) for row in transactions), 2),
            "date_from": min(row["booking_date"] for row in transactions),
            "date_to": max(row["booking_date"] for row in transactions),
            "currencies": sorted({row["currency"] for row in transactions}),
            "categories": sorted({row["category"] for row in transactions}),
        },
    }
