"""Mise à jour jeux / mods — stub."""
from __future__ import annotations

import webbrowser
from typing import Any
from urllib.parse import quote_plus

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    query = (args.get("query") or "minecraft mods").strip()
    url = f"https://www.google.com/search?q={quote_plus(query + ' download')}"
    webbrowser.open(url)
    return SkillResult.ok(url=url, message=f"Recherche mods/jeux: {query} (stub Phase 1)")
