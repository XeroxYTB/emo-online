"""YouTube — ouvre recherche ou vidéo."""
from __future__ import annotations

import re
import webbrowser
from typing import Any
from urllib.parse import quote_plus

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    query = (args.get("query") or args.get("prompt") or "").strip()
    if not query:
        return SkillResult.fail("Requête YouTube requise")
    for w in ("youtube", "vidéo", "video", "yt", "cherche", "joue", "lance"):
        query = re.sub(rf"\b{w}\b", "", query, flags=re.I).strip()
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    webbrowser.open(url)
    return SkillResult.ok(url=url, message=f"YouTube: {query}")
