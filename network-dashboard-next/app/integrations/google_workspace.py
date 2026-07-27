from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]


class GoogleWorkspaceAdapter:
    def __init__(self, cache: TTLCache, breaker: CircuitBreaker, *, token_path: Path | None = None) -> None:
        self.cache = cache
        self.breaker = breaker
        self.token_path = token_path or (Path.home() / ".hermes" / "google_token.json")

    def _credentials(self):
        if not self.token_path.is_file():
            raise RuntimeError("Google-token saknas")
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2.credentials import Credentials

        credentials = Credentials.from_authorized_user_file(self.token_path, scopes=SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            self.token_path.write_text(credentials.to_json(), encoding="utf-8")
        if not credentials.valid:
            raise RuntimeError("Google-token är ogiltig")
        return credentials

    def status(self) -> dict[str, Any]:
        if not self.token_path.is_file():
            return {"configured": False, "authenticated": False, "status": "missing"}
        try:
            credentials = self._credentials()
            return {
                "configured": True,
                "authenticated": bool(credentials.valid),
                "status": "authenticated" if credentials.valid else "invalid",
                "scopes": sorted(credentials.scopes or []),
            }
        except Exception as exc:
            return {"configured": True, "authenticated": False, "status": "invalid", "error": str(exc)[:240]}

    def events(self, start: datetime | None = None, end: datetime | None = None, *, fresh: bool = False) -> dict[str, Any]:
        start = start or datetime.now(timezone.utc)
        end = end or start + timedelta(days=7)
        key = f"google:events:{start.isoformat()}:{end.isoformat()}"
        if fresh:
            self.cache.invalidate("google:events:")
        cached = self.cache.get(key)
        if cached is not None:
            return {**cached, "cache": "hit"}

        def loader() -> dict[str, Any]:
            from googleapiclient.discovery import build

            service = build("calendar", "v3", credentials=self._credentials(), cache_discovery=False)
            response = service.events().list(
                calendarId="primary",
                timeMin=start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                timeMax=end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                singleEvents=True,
                orderBy="startTime",
                maxResults=250,
            ).execute()
            events = []
            for row in response.get("items") or []:
                start_value = (row.get("start") or {}).get("dateTime") or (row.get("start") or {}).get("date")
                end_value = (row.get("end") or {}).get("dateTime") or (row.get("end") or {}).get("date")
                events.append({
                    "id": str(row.get("id") or ""),
                    "title": str(row.get("summary") or "(utan titel)")[:300],
                    "start": start_value,
                    "end": end_value,
                    "all_day": bool((row.get("start") or {}).get("date")),
                    "location": str(row.get("location") or "")[:300],
                    "description": str(row.get("description") or "")[:2000],
                    "html_link": str(row.get("htmlLink") or ""),
                })
            return {"ok": True, "events": events, "count": len(events)}

        try:
            payload = self.breaker.call("google-calendar", loader)
            self.cache.set(key, payload, 90)
            return {**payload, "cache": "miss"}
        except Exception as exc:
            return {"ok": False, "events": [], "count": 0, "error": str(exc)[:240], "breaker": self.breaker.status("google-calendar")}

    def tasks(self, *, fresh: bool = False) -> dict[str, Any]:
        key = "google:tasks:open"
        if fresh:
            self.cache.invalidate(key)
        cached = self.cache.get(key)
        if cached is not None:
            return {**cached, "cache": "hit"}

        def loader() -> dict[str, Any]:
            from googleapiclient.discovery import build

            service = build("tasks", "v1", credentials=self._credentials(), cache_discovery=False)
            tasklists = service.tasklists().list(maxResults=100).execute().get("items") or []
            tasks = []
            for tasklist in tasklists:
                response = service.tasks().list(
                    tasklist=tasklist["id"], showCompleted=False, showDeleted=False, showHidden=False, maxResults=100
                ).execute()
                for row in response.get("items") or []:
                    tasks.append({
                        "id": str(row.get("id") or ""),
                        "tasklist_id": str(tasklist.get("id") or ""),
                        "tasklist": str(tasklist.get("title") or "")[:200],
                        "title": str(row.get("title") or "")[:300],
                        "notes": str(row.get("notes") or "")[:2000],
                        "due": row.get("due"),
                        "status": str(row.get("status") or "needsAction"),
                    })
            tasks.sort(key=lambda row: (str(row.get("due") or "9999"), row["title"].casefold()))
            return {"ok": True, "tasks": tasks, "tasklists": tasklists, "count": len(tasks)}

        try:
            payload = self.breaker.call("google-tasks", loader)
            self.cache.set(key, payload, 90)
            return {**payload, "cache": "miss"}
        except Exception as exc:
            return {"ok": False, "tasks": [], "tasklists": [], "count": 0, "error": str(exc)[:240], "breaker": self.breaker.status("google-tasks")}

    def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=self._credentials(), cache_discovery=False)
        body = {
            "summary": payload["title"],
            "description": payload.get("description", ""),
            "location": payload.get("location", ""),
            "start": {"dateTime": payload["start"], "timeZone": "Europe/Mariehamn"},
            "end": {"dateTime": payload["end"], "timeZone": "Europe/Mariehamn"},
        }
        event = service.events().insert(calendarId="primary", body=body).execute()
        self.cache.invalidate("google:events:")
        return {"ok": True, "id": event.get("id"), "html_link": event.get("htmlLink")}

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        from googleapiclient.discovery import build

        service = build("tasks", "v1", credentials=self._credentials(), cache_discovery=False)
        tasklist_id = payload.get("tasklist_id") or "@default"
        body = {"title": payload["title"], "notes": payload.get("notes", "")}
        if payload.get("due"):
            body["due"] = payload["due"]
        task = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
        self.cache.invalidate("google:tasks:")
        return {"ok": True, "id": task.get("id")}
