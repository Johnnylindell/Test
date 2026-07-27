from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "static" / "live" / "app.js"
HTML = ROOT / "static" / "live" / "index.html"
CSS = ROOT / "static" / "shared" / "app.css"


def test_family_frontend_exposes_core_and_subviews() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    for view in (
        "home",
        "planning",
        "family",
        "food",
        "more",
        "shopping",
        "inventory",
        "wishlists",
        "household",
        "dashboard",
    ):
        assert f"{view}:" in script


def test_family_frontend_uses_current_api_contracts() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    for endpoint in (
        "/api/v2/home/summary",
        "/api/v2/planning/overview",
        "/api/v2/family/overview",
        "/api/v2/food/overview",
        "/api/v2/shopping/overview",
        "/api/v2/inventory/overview",
        "/api/v2/wishlists/overview",
        "/api/v2/household/overview",
        "/api/v2/experience/my-dashboard",
        "/api/v2/experience/quests",
    ):
        assert endpoint in script
    assert "routine_rules" in script
    assert "routine_instances" in script
    assert "checklist_items" in script
    assert "data.days ||" not in script


def test_family_frontend_contains_mutation_workflows() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    expected = (
        "reminder-create",
        "routine-create",
        "family-list-item",
        "meal-set",
        "recipe-create",
        "shopping-create",
        "inventory-create",
        "wishlist-create",
        "household-create",
        "forget-create",
        "shopping-toggle",
        "inventory-place",
        "recipe-shopping",
        "quest-toggle",
    )
    for workflow in expected:
        assert workflow in script


def test_family_frontend_shows_safe_runtime_mode() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    assert 'home.runtime?.read_only' in script
    assert 'state.readOnly ? " disabled"' in script
    assert "Skrivskyddat parallelläge" in script
    assert 'id="runtime-mode"' in html
    assert 'id="app-notice"' in html


def test_family_styles_support_mobile_subviews() -> None:
    css = CSS.read_text(encoding="utf-8")
    assert ".quick-grid" in css
    assert ".inline-form" in css
    assert "@media (max-width: 430px)" in css
