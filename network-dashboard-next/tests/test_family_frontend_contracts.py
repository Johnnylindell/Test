from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "static" / "live" / "app.js"
PWA = ROOT / "static" / "live" / "pwa.js"
WORKER = ROOT / "static" / "live" / "sw.js"
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
        "/api/v2/experience/compass",
        "/api/v2/experience/search",
        "/api/v2/presence/overview",
        "/api/v2/food/recipes/import/preview",
    ):
        assert endpoint in script
    assert "routine_rules" in script
    assert "routine_instances" in script
    assert "checklist_items" in script
    assert "smart_suggestions" in script
    assert "data.days ||" not in script


def test_family_frontend_contains_mutation_workflows() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    expected = (
        "reminder-create",
        "routine-create",
        "family-list-item",
        "meal-set",
        "recipe-create",
        "recipe-import-preview",
        "recipe-import-save",
        "shopping-create",
        "shopping-suggestion-add",
        "shopping-suggestion-dismiss",
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


def test_family_frontend_initializes_runtime_before_direct_route() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    bootstrap = script.split("async function bootstrap()", 1)[1]
    assert "const [access, home] = await Promise.all" in bootstrap
    assert "updateRuntime(home);" in bootstrap
    assert "await openView" in bootstrap
    assert bootstrap.index("updateRuntime(home);") < bootstrap.index("await openView")


def test_family_frontend_shows_safe_runtime_mode() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    assert "home.runtime?.read_only" in script
    assert 'state.readOnly ? " disabled"' in script
    assert "Skrivskyddat parallelläge" in script
    assert 'id="runtime-mode"' in html
    assert 'id="app-notice"' in html


def test_family_shell_matches_approved_navigation_and_actions() -> None:
    html = HTML.read_text(encoding="utf-8")
    for identifier in (
        'id="search-button"',
        'id="notification-button"',
        'id="new-button"',
        'id="profile-button"',
        'id="search-dialog"',
        'id="new-dialog"',
        'id="profile-dialog"',
    ):
        assert identifier in html
    for view in ("home", "planning", "food", "family", "more"):
        assert f'data-view="{view}"' in html


def test_family_styles_support_responsive_finished_ui() -> None:
    css = CSS.read_text(encoding="utf-8")
    for selector in (
        ".topbar--family",
        ".quick-grid",
        ".inline-form",
        ".sheet",
        ".recipe-preview",
        ".presence-grid",
        ".nav--family",
        ".admin-grid",
    ):
        assert selector in css
    assert "@media (max-width: 760px)" in css
    assert "@media (max-width: 520px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_pwa_never_caches_api_or_admin_requests() -> None:
    pwa = PWA.read_text(encoding="utf-8")
    worker = WORKER.read_text(encoding="utf-8")
    assert 'navigator.serviceWorker.register("/sw.js"' in pwa
    assert "/api/v2/notifications/subscriptions" in pwa
    assert 'url.pathname.startsWith("/api/")' in worker
    assert 'url.pathname.startsWith("/preview-v2")' in worker
    assert "Promise.allSettled" in worker
