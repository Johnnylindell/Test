from __future__ import annotations

from pathlib import Path

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker
from app.database.database import Database
from app.integrations.config_store import IntegrationConfigStore
from app.integrations.home_assistant import HomeAssistantAdapter
from app.modules.budget.excel import BudgetExcelWorkbook
from app.modules.home_assistant.service import HomeLifeService


def test_budget_excel_roundtrip_preserves_cells_and_metadata() -> None:
    payload = {
        "format": "network-dashboard-budget-v1",
        "exported_at": "2026-07-27T12:00:00+00:00",
        "sheets": [
            {
                "name": "Januari 2027",
                "kind": "month",
                "sort_order": 1,
                "max_row": 40,
                "max_col": 12,
                "cells": [
                    {"row_num": 1, "col_num": 1, "value": "Kategori"},
                    {"row_num": 18, "col_num": 1, "value": "Mat"},
                    {"row_num": 18, "col_num": 2, "value": "125.5"},
                    {"row_num": 20, "col_num": 3, "value": "=SUM(B18:B19)"},
                ],
            }
        ],
    }
    data = BudgetExcelWorkbook.export(payload)
    parsed = BudgetExcelWorkbook.parse(data)
    assert parsed["format"] == payload["format"]
    assert parsed["summary"] == {"sheets": 1, "cells": 4, "names": ["Januari 2027"]}
    assert parsed["sheets"][0]["kind"] == "month"
    cells = {(row["row_num"], row["col_num"]): row["value"] for row in parsed["sheets"][0]["cells"]}
    assert cells[(18, 1)] == "Mat"
    assert cells[(18, 2)] == "125.5"
    assert cells[(20, 3)] == "=SUM(B18:B19)"


def test_budget_excel_rejects_unversioned_workbook() -> None:
    from io import BytesIO

    from openpyxl import Workbook

    workbook = Workbook()
    stream = BytesIO()
    workbook.save(stream)
    try:
        BudgetExcelWorkbook.parse(stream.getvalue())
    except ValueError as exc:
        assert "versionsmetadata" in str(exc)
    else:
        raise AssertionError("Unversioned workbook should be rejected")


class StubHomeAssistant(HomeAssistantAdapter):
    def __init__(self) -> None:
        pass

    def entities(self, *, fresh: bool = False) -> dict:
        return {
            "configured": True,
            "ok": True,
            "entities": [
                {"entity_id": "light.kok", "domain": "light", "name": "Kökslampa", "state": "on"},
                {"entity_id": "cover.garage", "domain": "cover", "name": "Garageport", "state": "closed"},
                {"entity_id": "climate.vardagsrum", "domain": "climate", "name": "Vardagsrum", "state": "heat"},
            ],
            "cache": "miss",
        }


class StubUnconfiguredHomeAssistant(HomeAssistantAdapter):
    def __init__(self) -> None:
        pass

    def entities(self, *, fresh: bool = False) -> dict:
        return {
            "configured": False,
            "ok": False,
            "state": "setup_required",
            "message": "Home Assistant-token saknas",
            "missing": ["token"],
            "setup": {"url": True, "token": False},
            "entities": [],
            "cache": "miss",
        }


def _integration_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "integration.sqlite3")
    with database.transaction() as connection:
        connection.execute("CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
        connection.execute("CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
    return database


def test_home_life_projection_groups_and_sanitizes_entities(tmp_path) -> None:
    database = Database(tmp_path / "home.sqlite3")
    with database.transaction() as connection:
        connection.execute("CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
    service = HomeLifeService(database, StubHomeAssistant())
    service.save_favorites(["light.kok"])
    result = service.overview()
    assert result["ok"] is True
    assert result["summary"] == {"entities": 3, "active": 2, "favorites": 1, "groups": 3}
    assert result["sensitive_values_exposed"] is False
    first = result["groups"][0]["entities"][0]
    assert first["entity_id"] == "light.kok"
    assert first["favorite"] is True
    assert "turn_on" in first["services"]


def test_home_assistant_reports_each_missing_configuration_component(tmp_path) -> None:
    database = _integration_database(tmp_path)
    store = IntegrationConfigStore(database, tmp_path / "integration-secrets.json")
    adapter = HomeAssistantAdapter(store, TTLCache(), CircuitBreaker())

    missing_both = adapter.status()
    assert missing_both["configured"] is False
    assert missing_both["state"] == "setup_required"
    assert missing_both["missing"] == ["url", "token"]
    assert missing_both["setup"] == {"url": False, "token": False}

    store.set("home_assistant_url", "http://homeassistant.local:8123")
    missing_token = adapter.status(fresh=True)
    assert missing_token["missing"] == ["token"]
    assert missing_token["setup"] == {"url": True, "token": False}
    assert missing_token["message"] == "Home Assistant-token saknas"

    store.clear("home_assistant_url")
    store.set("home_assistant_token", "test-home-assistant-token-1234567890")
    missing_url = adapter.status(fresh=True)
    assert missing_url["missing"] == ["url"]
    assert missing_url["setup"] == {"url": False, "token": True}
    assert missing_url["message"] == "Home Assistant URL saknas"
    assert missing_url["sensitive_values_exposed"] is False


def test_home_life_projection_preserves_safe_setup_diagnostics(tmp_path) -> None:
    database = Database(tmp_path / "home-unconfigured.sqlite3")
    with database.transaction() as connection:
        connection.execute("CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
    result = HomeLifeService(database, StubUnconfiguredHomeAssistant()).overview()
    assert result["configured"] is False
    assert result["missing"] == ["token"]
    assert result["setup"] == {"url": True, "token": False}
    assert result["message"] == "Home Assistant-token saknas"
    assert result["groups"] == []


def test_home_life_source_does_not_return_tokens_or_urls() -> None:
    source = Path("app/modules/home_assistant/service.py").read_text(encoding="utf-8")
    assert '"token"' not in source
    assert '"home_assistant_url"' not in source
    assert '"sensitive_values_exposed": False' in source


def test_home_assistant_frontend_explains_partial_setup_without_values() -> None:
    source = Path("static/live/home-assistant.js").read_text(encoding="utf-8")
    assert 'missing.has("token")' in source
    assert 'missing.has("url")' in source
    assert "long-lived access token" in source
    assert "HOME_ASSISTANT_TOKEN" not in source
