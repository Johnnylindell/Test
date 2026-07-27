from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_login
from app.auth.service import Identity

router = APIRouter(prefix="/api/v2/weather", tags=["weather"])


@router.get("/forecast")
def forecast(request: Request, fresh: bool = False, _: Identity = Depends(require_login)) -> dict:
    return request.app.state.weather.forecast(fresh=fresh)
