from pathlib import Path


def test_assistant_admin_workspace_is_loaded() -> None:
    index = Path("static/v2/index.html").read_text(encoding="utf-8")
    assert '<script type="module" src="/preview-v2/assistant-admin.js"></script>' in index


def test_assistant_admin_uses_safe_query_and_confirmation_contracts() -> None:
    source = Path("static/v2/assistant-admin.js").read_text(encoding="utf-8")
    assert 'query("/api/v2/assistant/query"' in source
    assert 'api("/api/v2/assistant/confirm"' in source
    assert 'api("/api/v2/admin/security/overview")' in source
    assert 'currentResult?.proposal?.token' in source
    assert "JSON.stringify" not in source
    assert 'target.origin !== location.origin' in source
    assert 'location.hash = target.hash || "#home"' in source
    assert 'history.replaceState(null, "", "#assistant-admin")' in source
    assert 'data-assistant-admin-view' in source


def test_assistant_admin_does_not_embed_proposal_token_in_markup() -> None:
    source = Path("static/v2/assistant-admin.js").read_text(encoding="utf-8")
    result_renderer = source.split("function renderResult()", 1)[1].split("function render()", 1)[0]
    assert "proposal.token" not in result_renderer
    assert "Token visas inte" in source
