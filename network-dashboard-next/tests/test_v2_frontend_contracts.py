from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V2_SCRIPT = ROOT / "static" / "v2" / "app.js"
V2_HTML = ROOT / "static" / "v2" / "index.html"
SHARED_CSS = ROOT / "static" / "shared" / "app.css"


def test_v2_exposes_migrated_admin_views() -> None:
    script = V2_SCRIPT.read_text(encoding="utf-8")
    for view in (
        "overview",
        "budget",
        "calendar",
        "notifications",
        "wishlists",
        "household",
        "security",
        "backups",
        "integrations",
        "homelab",
    ):
        assert f'{view}: {{ label:' in script

    for endpoint in (
        "/api/v2/budget/year",
        "/api/v2/budget/sync",
        "/api/v2/calendar/overview",
        "/api/v2/notifications/checks",
        "/api/v2/wishlists/overview",
        "/api/v2/household/overview",
        "/api/v2/admin/security/overview",
        "/api/v2/admin/backups",
    ):
        assert endpoint in script


def test_v2_shell_loads_every_modular_workspace() -> None:
    html = V2_HTML.read_text(encoding="utf-8")
    assets = (
        "excel.js",
        "configuration.js",
        "access.js",
        "banking.js",
        "operations.js",
        "configuration.css",
        "operations.css",
    )
    for asset in assets:
        assert asset in html
        assert (ROOT / "static" / "v2" / asset).is_file()

    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "banking_router" in main
    assert "operations_router" in main
    assert "app.include_router(banking_router)" in main
    assert "app.include_router(operations_router)" in main


def test_v2_budget_export_does_not_shadow_browser_document() -> None:
    script = V2_SCRIPT.read_text(encoding="utf-8")
    assert 'const document = await api("/api/v2/budget/export")' not in script
    assert 'const exportedBudget = await api("/api/v2/budget/export")' in script
    assert 'document.createElement("a")' in script


def test_v2_displays_runtime_safety_mode() -> None:
    html = V2_HTML.read_text(encoding="utf-8")
    script = V2_SCRIPT.read_text(encoding="utf-8")
    assert 'id="v2-mode"' in html
    assert 'id="v2-notice"' in html
    assert "Skrivskyddat parallelläge" in script
    assert "state.readOnly" in script
    assert "state.externalSideEffects" in script


def test_shared_styles_cover_forms_and_mobile_admin() -> None:
    css = SHARED_CSS.read_text(encoding="utf-8")
    for selector in (".form", ".field", ".mode-banner", ".row__actions", ".admin-grid"):
        assert selector in css
    assert "@media (max-width: 760px)" in css
