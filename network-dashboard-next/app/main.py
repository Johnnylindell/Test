from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.auth.service import AuthService
from app.compat.legacy_proxy import router as legacy_proxy_router
from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker
from app.core.config import settings
from app.core.ports import choose_port
from app.database.database import Database
from app.integrations.home_assistant import HomeAssistantAdapter
from app.integrations.tailscale import TailscaleAdapter
from app.modules.admin_integrations.router import router as admin_integrations_router
from app.modules.budget.router import router as budget_router
from app.modules.family.router import router as family_router
from app.modules.food.router import router as food_router
from app.modules.health.router import router as health_router
from app.modules.home.router import router as home_router
from app.modules.homelab.router import router as homelab_router
from app.modules.inventory.router import router as inventory_router
from app.modules.notifications.router import router as notifications_router
from app.modules.planning.router import router as planning_router
from app.modules.shopping.router import router as shopping_router
from app.web.router import router as web_router

logger = logging.getLogger("network-dashboard-next")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.5.0")
    database = Database(settings.database_path)
    selected_port = choose_port(settings.port)
    cache = TTLCache()
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30)

    app.state.settings = settings
    app.state.database = database
    app.state.auth_service = AuthService(database, settings)
    app.state.selected_port = selected_port
    app.state.cache = cache
    app.state.circuit_breaker = breaker
    app.state.home_assistant = HomeAssistantAdapter(database, cache, breaker)
    app.state.tailscale = TailscaleAdapter(cache, breaker, selected_port)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error", extra={"request_id": request_id})
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_error",
                        "message": "Ett internt serverfel uppstod.",
                        "request_id": request_id,
                    }
                },
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(home_router)
    app.include_router(planning_router)
    app.include_router(family_router)
    app.include_router(shopping_router)
    app.include_router(inventory_router)
    app.include_router(food_router)
    app.include_router(budget_router)
    app.include_router(notifications_router)
    app.include_router(homelab_router)
    app.include_router(admin_integrations_router)
    app.include_router(web_router)
    app.include_router(legacy_proxy_router)
    return app


app = create_app()


def selected_port() -> int:
    return int(app.state.selected_port)
