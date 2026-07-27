from __future__ import annotations

import os
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
    def __init__(
        self,
        cache: TTLCache,
        breaker: CircuitBreaker,
        *,
        token_path: Path | None = None,
        client_secrets_path: Path | None = None,
        persist_token_refresh: bool = False,
    ) -> None:
        self.cache = cache
        self.breaker = breaker
        self.token_path = token_path or (Path.home() / ".config" / "network-dashboard-next" / "google_token.json")
        self.client_secrets_path = client_secrets_path or (
            Path.home() / ".config" / "network-dashboard-next" / "google_client_secret.json"
        )
        self.persist_token_refresh = persist_token_refresh

    def _write_token(self, payload: str) -> None:
        if not self.persist_token_refresh:
            raise RuntimeError("Google-token får inte skrivas när externa sidoeffekter är avstängda")
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.token_path.with_suffix(self.token_path.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.token_path)
        os.chmod(self.token_path, 0o600)

    def _credentials(self):
        if not self.token_path.is_file():
            raise RuntimeError("Google-token saknas")
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2.credentials import Credentials

        credentials = Credentials.from_authorized_user_file(self.token_path, scopes=SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            if self.persist_token_refresh:
                self._write_token(credentials.to_json())
        if not credentials.valid:
            raise RuntimeError("Google-token är ogiltig")
        return credentials

    def status(self) -> dict[str, Any]:
        result = {
            "configured": self.token_path.is_file(),
            "client_configured": self.client_secrets_path.is_file(),
            "authenticated": False,
            "status": "missing",
            "scopes": [],
            "token_refresh_persisted": self.persist_token_refresh,
        }
        if not self.token_path.is_file():
            return result
        try:
            credentials = self._credentials()
            return {
                **result,
                "authenticated": bool(credentials.valid),
                "status": "authenticated" if credentials.valid else "invalid",
                "scopes": sorted(credentials.scopes or []),
            }
        except Exception as exc:
            return {**result, "status": "invalid", "error": str(exc)[:240]}

    def begin_oauth(self, redirect_uri: str) -> dict[str, Any]:
        if not self.persist_token_refresh:
            raise RuntimeError("Google OAuth är avstängt när externa sidoeffekter är avstängda")
        if not self.client_secrets_path.is_file():
            raise RuntimeError("Google client secret saknas")
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_secrets_file(
            str(self.client_secrets_path),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            autogenerate_code_verifier=True,
        )
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return {
            "ok": True,
            "authorization_url": authorization_url,
            "state": state,
            "code_verifier": flow.code_verifier or "",
        }

    def complete_oauth(
        self,
        *,
        authorization_response: str,
        redirect_uri: str,
        state: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        if not self.persist_token_refresh:
            raise RuntimeError("Google OAuth är avstängt när externa sidoeffekter är avstängda")
        if not self.client_secrets_path.is_file():
            raise RuntimeError("Google client secret saknas")
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_secrets_file(
            str(self.client_secrets_path),
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier or None,
        )
        flow.fetch_token(authorization_response=authorization_response)
        self._write_token(flow.credentials.to_json())
        self.cache.invalidate("google:")
        return {"ok": True, "authenticated": True, "scopes": sorted(flow.credentials.scopes or [])}

    def disconnect(self) -> dict[str, Any]:
        if not self.persist_token_refresh:
            raise RuntimeError("Google-token får inte tas bort när externa sidoeffekter är avstängda")
        removed = self.token_path.is_file()
        self.token_path.unlink(missing_ok=True)
        self.cache.invalidate("google:")
        return {"ok": True, "removed": removed}

    def calendars(self, *, fresh: bool = False) -> dict[str, Any]:
        key = "google:calendars"
        if fresh:
            self.cache.invalidate(key)
        cached = self.cache.get(key)
        if cached is not None:
            return {**cached, "cache": "hit"}

        def loader() -> dict[str, Any]:
            from googleapiclient.discovery import build

            service = build("calendar", "v3", credentials=self._credentials(), cache_discovery=False)
            page_token = None
            rows: list[dict[str, Any]] = []
            while True:
                response = service.calendarList().list(
                    maxResults=250,
                    pageToken=page_token,
                    showHidden=False,
                ).execute()
                for item in response.get("items") or []:
                    rows.append({
                        "id": str(item.get("id") or ""),
                        "title": str(item.get("summaryOverride") or item.get("summary") or "Kalender")[:200],
                        "primary": bool(item.get("primary")),
                        "selected": bool(item.get("selected", True)),
                        "access_role": str(item.get("accessRole") or "")[:40],
                        "background_color": str(item.get("backgroundColor") or "")[:20],
                    })
                page_token = response.get("nextPageToken")
                if not page_token or len(rows) >= 500:
                    break
            rows.sort(key=lambda row: (not row["primary"], row["title"].casefold()))
            return {"ok": True, "calendars": rows, "count": len(rows)}

        try:
            payload = self.breaker.call("google-calendars", loader)
            self.cache.set(key, payload, 300)
            return {**payload, "cache": "miss"}
        except Exception as exc:
            return {
                "ok": False,
                "calendars": [],
                "count": 0,
                "error": str(exc)[:240],
                "breaker": self.breaker.status("google-calendars"),
            }

    def events(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        *,
        calendar_id: str = "primary",
        fresh: bool = False,
    ) -> dict[str, Any]:
        start = start or datetime.now(timezone.utc)
        end = end or start + timedelta(days=7)
        selected = str(calendar_id or "primary")[:1000]
        key = f"google:events:{selected}:{start.isoformat()}:{end.isoformat()}"
        if fresh:
            self.cache.invalidate("google:events:")
        cached = self.cache.get(key)
        if cached is not None:
            return {**cached, "cache": "hit"}

        def loader() -> dict[str, Any]:
            from googleapiclient.discovery import build

            service = build("calendar", "v3", credentials=self._credentials(), cache_discovery=False)
            response = service.events().list(
                calendarId=selected,
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
                    "calendar_id": selected,
                    "title": str(row.get("summary") or "(utan titel)")[:300],
                    "start": start_value,
                    "end": end_value,
                    "all_day": bool((row.get("start") or {}).get("date")),
                    "location": str(row.get("location") or "")[:300],
                    "description": str(row.get("description") or "")[:2000],
                    "html_link": str(row.get("htmlLink") or ""),
                })
            return {"ok": True, "calendar_id": selected, "events": events, "count": len(events)}

        try:
            payload = self.breaker.call("google-calendar", loader)
            self.cache.set(key, payload, 90)
            return {**payload, "cache": "miss"}
        except Exception as exc:
            return {
                "ok": False,
                "calendar_id": selected,
                "events": [],
                "count": 0,
                "error": str(exc)[:240],
                "breaker": self.breaker.status("google-calendar"),
            }

    def tasks(self, *, fresh: bool = False) -> dict[str, Any]:
        key = "google:tasks:open"
        if fresh:
            self.cache.invalidate("google:tasks:")
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
                    tasklist=tasklist["id"],
                    showCompleted=False,
                    showDeleted=False,
                    showHidden=False,
                    maxResults=100,
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
            return {
                "ok": False,
                "tasks": [],
                "tasklists": [],
                "count": 0,
                "error": str(exc)[:240],
                "breaker": self.breaker.status("google-tasks"),
            }

    def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=self._credentials(), cache_discovery=False)
        calendar_id = str(payload.get("calendar_id") or "primary")[:1000]
        body = {
            "summary": payload["title"],
            "description": payload.get("description", ""),
            "location": payload.get("location", ""),
            "start": {"dateTime": payload["start"], "timeZone": "Europe/Mariehamn"},
            "end": {"dateTime": payload["end"], "timeZone": "Europe/Mariehamn"},
        }
        event = service.events().insert(calendarId=calendar_id, body=body).execute()
        self.cache.invalidate("google:events:")
        return {
            "ok": True,
            "id": event.get("id"),
            "calendar_id": calendar_id,
            "html_link": event.get("htmlLink"),
        }

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        from googleapiclient.discovery import build

        service = build("tasks", "v1", credentials=self._credentials(), cache_discovery=False)
        tasklist_id = payload.get("tasklist_id") or "@default"
        body = {"title": payload["title"], "notes": payload.get("notes", "")}
        if payload.get("due"):
            body["due"] = payload["due"]
        task = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
        self.cache.invalidate("google:tasks:")
        return {"ok": True, "id": task.get("id"), "tasklist_id": tasklist_id}

    def update_task(self, tasklist_id: str, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from googleapiclient.discovery import build

        service = build("tasks", "v1", credentials=self._credentials(), cache_discovery=False)
        body: dict[str, Any] = {}
        for key in ("title", "notes", "due"):
            if key in payload:
                body[key] = payload[key]
        task = service.tasks().patch(tasklist=tasklist_id, task=task_id, body=body).execute()
        self.cache.invalidate("google:tasks:")
        return {"ok": True, "task": task}

    def set_task_completed(self, tasklist_id: str, task_id: str, completed: bool) -> dict[str, Any]:
        from googleapiclient.discovery import build

        service = build("tasks", "v1", credentials=self._credentials(), cache_discovery=False)
        body: dict[str, Any]
        if completed:
            body = {
                "status": "completed",
                "completed": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        else:
            body = {"status": "needsAction", "completed": None}
        task = service.tasks().patch(tasklist=tasklist_id, task=task_id, body=body).execute()
        self.cache.invalidate("google:tasks:")
        return {"ok": True, "task": task}

    def delete_task(self, tasklist_id: str, task_id: str) -> dict[str, Any]:
        from googleapiclient.discovery import build

        service = build("tasks", "v1", credentials=self._credentials(), cache_discovery=False)
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        self.cache.invalidate("google:tasks:")
        return {"ok": True, "task_id": task_id, "tasklist_id": tasklist_id}
