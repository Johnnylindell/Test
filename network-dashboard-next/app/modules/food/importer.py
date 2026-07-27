from __future__ import annotations

import ipaddress
import json
import socket
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture = False
        self._buffer: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "script":
            return
        values = {str(key).casefold(): str(value or "") for key, value in attrs}
        if values.get("type", "").casefold() == "application/ld+json":
            self._capture = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "script" and self._capture:
            self.blocks.append("".join(self._buffer))
            self._capture = False
            self._buffer = []


def _public_host(hostname: str) -> None:
    if not hostname:
        raise ValueError("Receptadressen saknar värdnamn")
    try:
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Receptsidan kunde inte hittas") from exc
    if not addresses:
        raise ValueError("Receptsidan kunde inte hittas")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Lokala eller privata nätadresser får inte importeras")


def _safe_url(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme.casefold() != "https":
        raise ValueError("Endast HTTPS-adresser stöds")
    if parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("Receptadressen innehåller otillåtna anslutningsuppgifter")
    _public_host(parsed.hostname or "")
    return parsed.geturl()


def _nodes(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        rows = [value]
        graph = value.get("@graph")
        if isinstance(graph, list):
            rows.extend(item for item in graph if isinstance(item, dict))
        return rows
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _is_recipe(row: dict[str, Any]) -> bool:
    kind = row.get("@type")
    values = kind if isinstance(kind, list) else [kind]
    return any(str(value or "").casefold() == "recipe" for value in values)


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, dict):
                text = str(item.get("text") or item.get("name") or "").strip()
                if text:
                    result.append(text)
        return result
    return []


def _image(value: Any, base_url: str) -> str:
    if isinstance(value, str):
        return urljoin(base_url, value)[:1200]
    if isinstance(value, list) and value:
        return _image(value[0], base_url)
    if isinstance(value, dict):
        return urljoin(base_url, str(value.get("url") or value.get("contentUrl") or ""))[:1200]
    return ""


class RecipeImporter:
    def __init__(self, *, timeout_seconds: float = 10.0, max_bytes: int = 1_500_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    def preview(self, url: str) -> dict[str, Any]:
        current = _safe_url(url)
        headers = {"User-Agent": "LindellsDashboardNext/1.0 recipe-import"}
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False, headers=headers) as client:
            for _ in range(4):
                response = client.get(current)
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location", "")
                    if not location:
                        raise ValueError("Receptsidan returnerade en tom omdirigering")
                    current = _safe_url(urljoin(current, location))
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").casefold()
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    raise ValueError("Adressen pekar inte på en HTML-sida")
                content = response.content
                if len(content) > self.max_bytes:
                    raise ValueError("Receptsidan är för stor")
                parser = _JsonLdParser()
                parser.feed(content.decode(response.encoding or "utf-8", errors="replace"))
                for block in parser.blocks[:30]:
                    try:
                        parsed = json.loads(block)
                    except (TypeError, json.JSONDecodeError):
                        continue
                    for row in _nodes(parsed):
                        if not _is_recipe(row):
                            continue
                        title = str(row.get("name") or "").strip()[:200]
                        ingredients = _text_list(row.get("recipeIngredient"))[:200]
                        steps = _text_list(row.get("recipeInstructions"))[:100]
                        if not title or not ingredients:
                            continue
                        publisher = row.get("publisher")
                        source_name = ""
                        if isinstance(publisher, dict):
                            source_name = str(publisher.get("name") or "")
                        source_name = (source_name or (urlparse(current).hostname or "Extern källa"))[:120]
                        servings = row.get("recipeYield")
                        if isinstance(servings, list):
                            servings = ", ".join(str(item) for item in servings)
                        return {
                            "ok": True,
                            "recipe": {
                                "title": title,
                                "source_url": current[:1200],
                                "source_name": str(source_name),
                                "image_url": _image(row.get("image"), current),
                                "ingredients": ingredients,
                                "steps": steps,
                                "tags": _text_list(row.get("keywords"))[:30],
                                "servings": str(servings or "")[:80],
                                "favorite": True,
                            },
                            "policy": {
                                "https_only": True,
                                "private_network_blocked": True,
                                "max_bytes": self.max_bytes,
                                "saved": False,
                            },
                        }
                raise ValueError("Ingen komplett Recipe JSON-LD hittades på sidan")
        raise ValueError("För många omdirigeringar")
