from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.modules.food.importer import RecipeImporter
from scripts.presence_bridge import collect_observations


class _Response:
    status_code = 200
    headers = {"content-type": "text/html; charset=utf-8"}
    encoding = "utf-8"
    content = b"""
    <html><head><script type="application/ld+json">
    {
      "@context":"https://schema.org",
      "@type":"Recipe",
      "name":"Testgryta",
      "recipeIngredient":["1 l vatten","2 morot"],
      "recipeInstructions":[{"@type":"HowToStep","text":"Koka."}],
      "recipeYield":"4 portioner",
      "publisher":{"name":"Exempel"}
    }
    </script></head></html>
    """

    def raise_for_status(self) -> None:
        return None


class _Client:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def get(self, url: str):
        return _Response()


def test_recipe_import_rejects_private_network() -> None:
    with pytest.raises(ValueError, match="privata nätadresser"):
        RecipeImporter().preview("https://127.0.0.1/recept")


def test_recipe_import_extracts_json_ld(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.food.importer.socket.getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))])
    monkeypatch.setattr(httpx, "Client", _Client)
    result = RecipeImporter().preview("https://example.com/recept")
    assert result["recipe"]["title"] == "Testgryta"
    assert result["recipe"]["ingredients"] == ["1 l vatten", "2 morot"]
    assert result["policy"]["saved"] is False


def test_presence_bridge_only_uses_explicit_mappings() -> None:
    state = {
        "updated_at": "2026-07-27T12:00:00+00:00",
        "devices": {
            "a": {"mac": "AA-BB-CC-DD-EE-FF", "is_present": True},
            "b": {"mac": "11:22:33:44:55:66", "is_present": True},
        },
    }
    config = {
        "devices": [
            {"source_identifier": "aa:bb:cc:dd:ee:ff", "owner": "Johnny", "enabled": True},
            {"source_identifier": "77:88:99:aa:bb:cc", "owner": "Kristina", "enabled": False},
        ]
    }
    observations = collect_observations(state, config)
    assert observations == [
        {
            "source_identifier": "aa:bb:cc:dd:ee:ff",
            "present": True,
            "observed_at": "2026-07-27T12:00:00+00:00",
        }
    ]
    assert "11:22:33:44:55:66" not in str(observations)


def test_calendar_oauth_contract_is_single_use() -> None:
    source = Path("app/modules/calendar/router.py").read_text(encoding="utf-8")
    assert 'set_json_state(f"google_oauth:{oauth_state}"' in source
    assert "request.app.state.database.set_json_state(key, {})" in source
    assert "timedelta(minutes=10)" in source
    assert "secrets.compare_digest" in source


def test_google_token_is_isolated_from_legacy() -> None:
    source = Path("app/integrations/google_workspace.py").read_text(encoding="utf-8")
    assert '"network-dashboard-next" / "google_token.json"' in source
    assert "google_token.json\")" not in source.split("network-dashboard-next", 1)[0]
    assert "os.chmod(self.token_path, 0o600)" in source
