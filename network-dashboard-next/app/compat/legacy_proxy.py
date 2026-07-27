from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["legacy-compat"])

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length",
}
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MIGRATED_PATHS = {
    "health", "homelab", "smart-home", "homeassistant", "family", "family-lists",
    "inventory", "weekly-meals", "budget", "budget-sheet", "budget-year",
    "alerts", "notifications/subscribe", "push-subscribe", "push-unsubscribe",
}
REPLACEMENTS = {
    "health": "/api/v2/health/ready",
    "homelab": "/api/v2/admin/homelab/overview",
    "smart-home": "/api/v2/admin/integrations/home-assistant/entities",
    "homeassistant": "/api/v2/admin/integrations/home-assistant/status",
    "family": "/api/v2/family/overview",
    "family-lists": "/api/v2/family/overview",
    "inventory": "/api/v2/inventory/overview",
    "weekly-meals": "/api/v2/food/overview",
    "budget": "/api/v2/budget/overview",
    "budget-sheet": "/api/v2/budget/overview",
    "budget-year": "/api/v2/budget/overview",
    "alerts": "/api/v2/notifications/overview",
    "notifications/subscribe": "/api/v2/notifications/subscriptions",
    "push-subscribe": "/api/v2/notifications/subscriptions",
    "push-unsubscribe": "/api/v2/notifications/subscriptions",
}


def _migrated(path: str) -> str | None:
    normalized = path.strip("/")
    for migrated in MIGRATED_PATHS:
        if normalized == migrated or normalized.startswith(migrated + "/"):
            return REPLACEMENTS.get(migrated)
    return None


@router.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_legacy_api(path: str, request: Request) -> Response:
    if path.startswith("v2/"):
        return Response(status_code=404)
    replacement = _migrated(path)
    if replacement:
        return Response(
            content=f'{{"error":"legacy_endpoint_retired","replacement":"{replacement}"}}',
            status_code=410,
            media_type="application/json",
            headers={"Deprecation": "true", "Link": f'<{replacement}>; rel="successor-version"'},
        )
    if request.method.upper() in MUTATING_METHODS and not request.app.state.settings.allow_legacy_writes:
        return Response(
            content='{"error":"legacy_writes_disabled"}',
            status_code=423,
            media_type="application/json",
        )

    target = f"{request.app.state.settings.legacy_origin}/api/{path}"
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP and key.lower() != "host"
    }
    body = await request.body()
    timeout = httpx.Timeout(20.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            upstream = await client.request(
                request.method, target, params=request.query_params, headers=headers, content=body
            )
    except httpx.HTTPError:
        return Response(
            content='{"error":"legacy_upstream_unavailable"}',
            status_code=502,
            media_type="application/json",
        )

    response_headers = {
        key: value for key, value in upstream.headers.items()
        if key.lower() not in HOP_BY_HOP and key.lower() != "set-cookie"
    }
    response_headers["Warning"] = '299 - "Legacy endpoint proxied to port 8792"'
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
