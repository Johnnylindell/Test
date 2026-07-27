from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker
from app.database.database import Database


class WeatherAdapter:
    def __init__(self, database: Database, cache: TTLCache, breaker: CircuitBreaker) -> None:
        self.database = database
        self.cache = cache
        self.breaker = breaker

    def _config(self) -> tuple[float, float, str]:
        lat = float(self.database.get_setting("weather_lat", 60.1) or 60.1)
        lon = float(self.database.get_setting("weather_lon", 19.9) or 19.9)
        label = str(self.database.get_setting("weather_label", "Åland") or "Åland")[:120]
        return lat, lon, label

    def forecast(self, *, fresh: bool = False) -> dict[str, Any]:
        lat, lon, label = self._config()
        key = f"weather:{lat:.4f}:{lon:.4f}"
        if fresh:
            self.cache.invalidate(key)
        cached = self.cache.get(key)
        if cached is not None:
            return {**cached, "cache": "hit"}

        def loader() -> dict[str, Any]:
            response = httpx.get(
                "https://api.met.no/weatherapi/locationforecast/2.0/compact",
                params={"lat": lat, "lon": lon},
                headers={"User-Agent": "LindellsDashboardNext/1.0 admin@lindell.local"},
                timeout=10,
            )
            response.raise_for_status()
            rows = response.json().get("properties", {}).get("timeseries", [])
            hourly = []
            for row in rows[:48]:
                details = row.get("data", {}).get("instant", {}).get("details", {})
                next_hour = row.get("data", {}).get("next_1_hours", {})
                hourly.append({
                    "time": row.get("time"),
                    "temperature_c": details.get("air_temperature"),
                    "wind_mps": details.get("wind_speed"),
                    "humidity_pct": details.get("relative_humidity"),
                    "precip_mm": next_hour.get("details", {}).get("precipitation_amount"),
                    "symbol": next_hour.get("summary", {}).get("symbol_code", ""),
                })
            daily_map: dict[str, dict[str, Any]] = {}
            for row in hourly:
                date = str(row.get("time") or "")[:10]
                if not date:
                    continue
                day = daily_map.setdefault(date, {"date": date, "temperatures": [], "precip_mm": 0.0, "symbols": []})
                if row.get("temperature_c") is not None:
                    day["temperatures"].append(float(row["temperature_c"]))
                day["precip_mm"] += float(row.get("precip_mm") or 0)
                if row.get("symbol"):
                    day["symbols"].append(row["symbol"])
            daily = []
            for day in list(daily_map.values())[:7]:
                temps = day.pop("temperatures")
                symbols = day.pop("symbols")
                day["min_c"] = min(temps) if temps else None
                day["max_c"] = max(temps) if temps else None
                day["precip_mm"] = round(day["precip_mm"], 1)
                day["symbol"] = max(set(symbols), key=symbols.count) if symbols else ""
                daily.append(day)
            return {
                "ok": True,
                "label": label,
                "source": "Met.no",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "current": hourly[0] if hourly else {},
                "hourly": hourly,
                "daily": daily,
            }

        try:
            payload = self.breaker.call("weather", loader)
            self.cache.set(key, payload, 120)
            return {**payload, "cache": "miss"}
        except Exception as exc:
            return {"ok": False, "label": label, "source": "Met.no", "error": str(exc)[:240], "hourly": [], "daily": []}
