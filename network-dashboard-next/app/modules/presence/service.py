from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.database.database import Database
from app.modules.notifications.repository import NotificationsRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


class PresenceService:
    def __init__(self, database: Database, hash_secret: str) -> None:
        self.database = database
        self.hash_secret = hash_secret.encode("utf-8")
        self.notifications = NotificationsRepository(database)

    def source_hash(self, source_id: str) -> str:
        value = " ".join(str(source_id or "").strip().lower().split())
        if len(value) < 4:
            raise ValueError("Enhetsidentifieraren är för kort")
        return hmac.new(self.hash_secret, value.encode("utf-8"), hashlib.sha256).hexdigest()

    def overview(self) -> dict[str, Any]:
        rows = self.database.fetch_all(
            "SELECT id,owner,label,notify_arrival,active,initialized,present,last_seen,last_checked,last_transition_at "
            "FROM presence_devices ORDER BY owner COLLATE NOCASE,label COLLATE NOCASE"
        ) if self.database.table_exists("presence_devices") else []
        people: dict[str, dict[str, Any]] = {}
        for row in rows:
            owner = str(row.get("owner") or "").strip()
            entry = people.setdefault(owner, {
                "owner": owner,
                "present": False,
                "devices_present": 0,
                "devices_total": 0,
                "last_seen": "",
                "configured": True,
            })
            if not row.get("active"):
                continue
            entry["devices_total"] += 1
            if row.get("present"):
                entry["present"] = True
                entry["devices_present"] += 1
            if str(row.get("last_seen") or "") > str(entry.get("last_seen") or ""):
                entry["last_seen"] = row.get("last_seen") or ""
        known = {str(profile.get("id") or profile.get("name") or "").strip().capitalize() for profile in self.database.get_json_state("family_profiles", []) if isinstance(profile, dict)}
        known.update({"Johnny", "Kristina", "Viktor", "Alfred"})
        normalized = {name.casefold() for name in people}
        for name in sorted(known):
            if name and name.casefold() not in normalized:
                people[name] = {
                    "owner": name,
                    "present": False,
                    "devices_present": 0,
                    "devices_total": 0,
                    "last_seen": "",
                    "configured": False,
                }
        events = self.database.fetch_all(
            "SELECT id,owner,event_type,message,created_at FROM presence_events ORDER BY created_at DESC LIMIT 100"
        ) if self.database.table_exists("presence_events") else []
        return {
            "ok": True,
            "mode": "hemma" if any(row["present"] for row in people.values()) else "borta",
            "people": sorted(people.values(), key=lambda row: (not row["present"], row["owner"].casefold())),
            "events": events,
            "privacy": {
                "raw_identifiers_stored": False,
                "raw_network_values_exposed": False,
            },
        }

    def register(self, owner: str, label: str, source_id: str, notify_arrival: bool = True) -> dict[str, Any]:
        clean_owner = str(owner or "").strip()[:80]
        if not clean_owner:
            raise ValueError("Namn krävs")
        source_hash = self.source_hash(source_id)
        now = _iso()
        existing = self.database.fetch_one("SELECT id FROM presence_devices WHERE source_hash=?", (source_hash,))
        device_id = str(existing["id"]) if existing else "presence-" + secrets.token_hex(8)
        self.database.execute(
            "INSERT INTO presence_devices(id,owner,label,source_hash,notify_arrival,active,created_at,updated_at) "
            "VALUES(?,?,?,?,?,1,?,?) ON CONFLICT(source_hash) DO UPDATE SET "
            "owner=excluded.owner,label=excluded.label,notify_arrival=excluded.notify_arrival,active=1,updated_at=excluded.updated_at",
            (device_id, clean_owner, str(label or f"{clean_owner}s telefon")[:120], source_hash, 1 if notify_arrival else 0, now, now),
        )
        return {"ok": True, "device": {"id": device_id, "owner": clean_owner, "label": str(label or f"{clean_owner}s telefon")[:120]}}

    def remove(self, device_id: str) -> bool:
        before = self.database.count("presence_devices", "id=?", (device_id,))
        self.database.execute("DELETE FROM presence_devices WHERE id=?", (device_id,))
        return before == 1

    def observe(self, source_id: str, present: bool, checked_at: str = "", cooldown_minutes: int = 15) -> dict[str, Any]:
        source_hash = self.source_hash(source_id)
        row = self.database.fetch_one("SELECT * FROM presence_devices WHERE source_hash=? AND active=1", (source_hash,))
        if not row:
            raise ValueError("Enheten är inte registrerad")
        now = _now()
        try:
            observed = datetime.fromisoformat(checked_at.replace("Z", "+00:00")) if checked_at else now
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            observed = observed.astimezone(timezone.utc)
        except ValueError:
            observed = now
        was_initialized = bool(row.get("initialized"))
        was_present = bool(row.get("present"))
        transition = was_initialized and was_present != bool(present)
        event_type = "arrival" if present else "departure"
        self.database.execute(
            "UPDATE presence_devices SET initialized=1,present=?,last_seen=?,last_checked=?,last_transition_at=?,updated_at=? WHERE id=?",
            (
                1 if present else 0,
                _iso(observed) if present else str(row.get("last_seen") or ""),
                _iso(observed),
                _iso(observed) if transition else str(row.get("last_transition_at") or ""),
                _iso(),
                row["id"],
            ),
        )
        created = None
        if transition:
            owner = str(row.get("owner") or "Familjemedlem")
            message = f"{owner} kom hem." if present else f"{owner} lämnade hemmet."
            event_id = "presence-event-" + secrets.token_hex(8)
            self.database.execute(
                "INSERT INTO presence_events(id,device_id,owner,event_type,message,created_at) VALUES(?,?,?,?,?,?)",
                (event_id, row["id"], owner, event_type, message, _iso(observed)),
            )
            if present and bool(row.get("notify_arrival")):
                cutoff = observed - timedelta(minutes=max(1, min(cooldown_minutes, 1440)))
                recent = self.database.fetch_value(
                    "SELECT COUNT(*) FROM presence_events WHERE owner=? AND event_type='arrival' AND created_at>=?",
                    (owner, _iso(cutoff)),
                    0,
                )
                if int(recent or 0) <= 1:
                    created = self.notifications.create_alert({
                        "id": "alert-" + secrets.token_hex(8),
                        "type": "arrival",
                        "message": message,
                        "severity": "normal",
                        "target": "family",
                        "created_at": _iso(observed),
                        "acknowledged_at": None,
                        "metadata": {"owner": owner, "presence_event_id": event_id},
                    })
        return {"ok": True, "initialized": was_initialized, "transition": transition, "present": bool(present), "alert": created}
