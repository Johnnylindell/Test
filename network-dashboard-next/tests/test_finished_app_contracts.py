from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_admin_password_has_no_insecure_default() -> None:
    auth = source("app/auth/service.py")
    installer = source("scripts/install_parallel.sh")
    assert 'os.getenv("HOMELAB_ADMIN_PASSWORD", "")' in auth
    assert 'os.getenv("HOMELAB_ADMIN_PASSWORD", "1234")' not in auth
    assert 'HOMELAB_ADMIN_PASSWORD="$(openssl rand -hex 12)"' in installer
    assert "ADMIN_PASSWORD_GENERATED=true" in installer
    assert "chmod 600 \"$ENV_FILE\"" in installer


def test_sessions_expose_an_iso_expiry_for_the_admin_ui() -> None:
    auth = source("app/auth/service.py")
    admin = source("static/v2/app.js")
    assert '"expires_at": datetime.fromtimestamp' in auth
    assert "dateTime(session.expires_at)" in admin


def test_home_assistant_mutations_require_external_side_effects() -> None:
    router = source("app/modules/admin_integrations/router.py")
    assert "def _require_external" in router
    assert "settings.read_only" in router
    assert "settings.external_side_effects" in router
    service_route = router.split('def home_assistant_service', 1)[1]
    assert "_require_external(request)" in service_route


def test_recipe_preview_has_a_read_only_get_route() -> None:
    router = source("app/modules/food/router.py")
    assert '@router.get("/recipes/import/preview")' in router
    preview = router.split('def preview_recipe_import_get', 1)[1]
    assert "RecipeImporter" in preview
    assert "food_repository" not in preview.split('@router.post("/recipes/import/preview"', 1)[0]


def test_presence_admin_response_never_exposes_source_values() -> None:
    service = source("app/modules/presence/service.py")
    router = source("app/modules/presence/router.py")
    devices = service.split("def devices", 1)[1].split("def overview", 1)[0]
    assert "source_hash" not in devices
    assert "source_id" not in devices
    assert '"source_hash_exposed": False' in router
    assert '"raw_network_values_exposed": False' in router


def test_compass_uses_sanitized_presence() -> None:
    router = source("app/modules/experience/router.py")
    assert "PresenceService" in router
    assert '.overview().get("people", [])' in router
    assert "presence=presence" in router


def test_admin_workspace_contains_all_finished_control_surfaces() -> None:
    script = source("static/v2/app.js")
    for view in (
        "overview",
        "budget",
        "calendar",
        "presence",
        "notifications",
        "wishlists",
        "household",
        "security",
        "backups",
        "integrations",
        "homelab",
    ):
        assert f"{view}: {{ label:" in script
    for endpoint in (
        "/api/v2/calendar/oauth/start",
        "/api/v2/calendar/events",
        "/api/v2/presence/devices",
        "/api/v2/admin/backups",
        "/api/v2/admin/security/access",
        "/api/v2/admin/integrations/home-assistant/service",
    ):
        assert endpoint in script
    assert "payload: budgetPayload" in script
    assert "document: budgetDocument" not in script


def test_entry_pages_share_the_finished_design() -> None:
    entry_css = source("static/shared/entry.css")
    chooser = source("static/live/choose-user.html")
    login = source("app/auth/router.py")
    assert ".entry__hero" in entry_css
    assert ".profile-grid" in entry_css
    assert 'value="alfred"' in chooser
    assert '/assets/entry.css' in chooser
    assert '/assets/entry.css' in login
