"""Météo — stub wttr.in (sans clé)."""
from __future__ import annotations

from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    query = (args.get("query") or args.get("city") or "Paris").strip()
    for w in ("météo", "meteo", "weather", "à", "a"):
        query = query.replace(w, "").strip()
    city = query or "Paris"
    if httpx is None:
        return SkillResult.fail("httpx requis")
    try:
        r = httpx.get(f"https://wttr.in/{city}?format=3", timeout=10)
        text = r.text.strip()
        return SkillResult.ok(city=city, report=text, message=text)
    except Exception as e:
        return SkillResult.fail(str(e))
