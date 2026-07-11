"""Recherche vols — stub lien Google Flights."""
from __future__ import annotations

import re
import webbrowser
from typing import Any
from urllib.parse import quote_plus

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    query = (args.get("query") or "").strip()
    if not query:
        return SkillResult.fail("Itinéraire requis (ex: Paris Londres)")
    clean = re.sub(r"\b(vol|flight|avion|cherche|trouve)\b", "", query, flags=re.I).strip()
    url = f"https://www.google.com/travel/flights?q={quote_plus(clean)}"
    webbrowser.open(url)
    return SkillResult.ok(url=url, message=f"Google Flights: {clean}")
