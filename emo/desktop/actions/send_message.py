"""Envoi message — stub (mailto / clipboard)."""
from __future__ import annotations

import webbrowser
from typing import Any
from urllib.parse import quote

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    text = (args.get("text") or args.get("message") or args.get("query") or "").strip()
    to = (args.get("to") or "").strip()
    if not text:
        return SkillResult.fail("Message requis")
    if "email" in text.lower() or "@" in to:
        url = f"mailto:{to}?body={quote(text)}"
        webbrowser.open(url)
        return SkillResult.ok(channel="email", message="Client mail ouvert")
    return SkillResult.ok(
        channel="stub",
        message=f"Message préparé (stub): {text[:100]}",
        hint="Configurez SMS/API en Phase 2",
    )
