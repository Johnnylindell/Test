from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from app.auth.service import Identity
from app.database.database import Database
from app.modules.experience.compass import HomeCompassService
from app.modules.experience.service import ExperienceService
from app.modules.family.repository import FamilyRepository
from app.modules.planning.repository import PlanningRepository
from app.modules.shopping.repository import ShoppingRepository


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * ((4 - len(value) % 4) % 4))


def _clean(value: str, limit: int = 500) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


class AssistantService:
    def __init__(self, database: Database, signing_secret: str) -> None:
        if len(signing_secret) < 32:
            raise ValueError("Assistentens signeringshemlighet är inte konfigurerad")
        self.database = database
        self.secret = signing_secret.encode("utf-8")
        self.experience = ExperienceService(database)

    def _proposal(self, identity: Identity, action: str, data: dict[str, Any], description: str) -> dict[str, Any]:
        expires = int(time.time()) + 600
        payload = {
            "version": 1,
            "expires": expires,
            "user": identity.user,
            "action": action,
            "data": data,
        }
        encoded = _b64(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        signature = _b64(hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest())
        return {
            "token": encoded + "." + signature,
            "description": description,
            "expires_at": datetime.fromtimestamp(expires, timezone.utc).isoformat(),
        }

    def _verify(self, token: str, identity: Identity) -> dict[str, Any]:
        try:
            encoded, supplied = token.split(".", 1)
            expected = _b64(hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest())
            if not hmac.compare_digest(supplied, expected):
                raise ValueError("Bekräftelsen har manipulerats")
            payload = json.loads(_unb64(encoded).decode("utf-8"))
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            if isinstance(exc, ValueError) and str(exc) == "Bekräftelsen har manipulerats":
                raise
            raise ValueError("Ogiltig bekräftelse") from exc
        if int(payload.get("expires") or 0) < int(time.time()):
            raise ValueError("Bekräftelsen har gått ut")
        if str(payload.get("user") or "") != identity.user:
            raise ValueError("Bekräftelsen tillhör en annan profil")
        if payload.get("version") != 1 or not isinstance(payload.get("data"), dict):
            raise ValueError("Bekräftelsen har fel format")
        return payload

    def query(self, message: str, identity: Identity) -> dict[str, Any]:
        text = _clean(message)
        lowered = text.casefold()
        if len(text) < 2:
            return self._reply("Skriv lite mer så kan jag hjälpa till.", "empty")

        shopping_match = re.search(
            r"(?:lägg|lagg|skriv)\s+(?:till\s+)?(.+?)\s+(?:på|pa|i)\s+inköpslistan$",
            lowered,
        )
        if not shopping_match:
            shopping_match = re.search(r"^(?:köp|kop)\s+(.+)$", lowered)
        if shopping_match:
            item = _clean(shopping_match.group(1), 300)
            proposal = self._proposal(
                identity,
                "shopping.add",
                {"text": item},
                f"Lägg till ”{item}” på inköpslistan",
            )
            return self._reply(
                f"Jag kan lägga till ”{item}” på inköpslistan.",
                "shopping_add",
                proposal=proposal,
            )

        reminder_match = re.search(r"^(?:påminn|paminn)\s+mig(?:\s+om)?\s+(.+)$", lowered)
        if reminder_match:
            title = _clean(reminder_match.group(1), 300)
            proposal = self._proposal(
                identity,
                "reminder.add",
                {"title": title, "owner": identity.user},
                f"Skapa påminnelsen ”{title}” för {identity.user}",
            )
            return self._reply(
                f"Jag kan skapa påminnelsen ”{title}”. Du kan sätta en exakt tid i Planera efteråt.",
                "reminder_add",
                proposal=proposal,
            )

        note_match = re.search(r"^(?:anteckna|skriv\s+upp|familjeanteckning)\s+(.+)$", lowered)
        if note_match:
            note = _clean(note_match.group(1), 1000)
            proposal = self._proposal(
                identity,
                "family.note",
                {"text": note, "owner": identity.user},
                "Spara texten som en familjeanteckning",
            )
            return self._reply("Jag kan spara det som en familjeanteckning.", "family_note", proposal=proposal)

        if any(phrase in lowered for phrase in ("vad ska jag göra", "vad är viktigast", "nästa steg", "home compass")):
            compass = HomeCompassService(self.database).overview(identity, weather={}, presence=[])
            actions = compass.get("actions") or []
            if not actions:
                return self._reply(compass.get("summary") or "Det är lugnt just nu.", "compass")
            return self._reply(
                compass.get("summary") or "Här är några bra nästa steg.",
                "compass",
                results=[
                    {
                        "title": row.get("title") or "Nästa steg",
                        "detail": row.get("detail") or "",
                        "url": f"/#{row.get('view') or 'home'}",
                    }
                    for row in actions[:4]
                ],
            )

        if lowered in {"hjälp", "vad kan du göra", "vad kan du gora"}:
            return self._reply(
                "Jag kan söka i appen och föreslå säkra åtgärder. Prova till exempel: ”var finns laddaren”, ”lägg mjölk på inköpslistan”, ”påminn mig om tandläkaren” eller ”vad ska jag göra?”.",
                "help",
            )

        search_text = text
        for prefix in ("var finns ", "sök ", "sok ", "hitta ", "har vi "):
            if lowered.startswith(prefix):
                search_text = text[len(prefix):].strip()
                break
        search = self.experience.search(search_text, identity)
        results = [
            {
                "title": row.get("title") or "Träff",
                "detail": row.get("detail") or row.get("kind") or "",
                "url": row.get("url") or "/#home",
            }
            for row in (search.get("results") or [])[:8]
        ]
        if results:
            return self._reply(f"Jag hittade {len(results)} träffar för ”{search_text}”.", "search", results=results)
        return self._reply(
            f"Jag hittade inget som matchar ”{search_text}”. Prova ett kortare sökord eller be mig lägga till något.",
            "search_empty",
        )

    @staticmethod
    def _reply(
        reply: str,
        intent: str,
        *,
        results: list[dict[str, Any]] | None = None,
        proposal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "reply": reply,
            "intent": intent,
            "results": results or [],
            "proposal": proposal,
            "requires_confirmation": proposal is not None,
            "network_model_used": False,
        }

    def confirm(self, token: str, identity: Identity) -> dict[str, Any]:
        payload = self._verify(token, identity)
        action = str(payload.get("action") or "")
        data = payload["data"]
        if action == "shopping.add":
            item_id = ShoppingRepository(self.database).add(
                {
                    "list_id": "shopping",
                    "text": _clean(data.get("text"), 300),
                    "quantity": 1,
                    "unit": "",
                    "category": "",
                    "store": "",
                },
                identity.user,
            )
            return {"ok": True, "action": action, "id": item_id, "message": "Varan lades till på inköpslistan."}
        if action == "reminder.add":
            reminder_id = PlanningRepository(self.database).add_reminder(
                {
                    "title": _clean(data.get("title"), 300),
                    "owner": identity.user,
                    "remind_at": "",
                    "note": "Skapad via assistenten",
                },
                identity.user,
            )
            return {"ok": True, "action": action, "id": reminder_id, "message": "Påminnelsen skapades."}
        if action == "family.note":
            note_id = FamilyRepository(self.database).add_note(
                _clean(data.get("text"), 1000),
                identity.user,
            )
            return {"ok": True, "action": action, "id": note_id, "message": "Familjeanteckningen sparades."}
        raise ValueError("Assistentåtgärden stöds inte")
