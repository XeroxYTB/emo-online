"""Rappels — persistance mémoire locale."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.memory import load_memory, save_memory


def run(args: dict) -> Any:
    text = (args.get("text") or args.get("query") or args.get("prompt") or "").strip()
    if not text:
        return SkillResult.fail("Texte du rappel requis")
    # Extraire le contenu après "rappelle(-moi)"
    m = re.search(r"rappelle(?:-moi)?\s+(?:de\s+)?(.+)", text, re.I)
    reminder_text = m.group(1).strip() if m else text

    mem = load_memory()
    reminders = mem.setdefault("reminders", [])
    entry = {
        "text": reminder_text,
        "created": datetime.now(timezone.utc).isoformat(),
        "done": False,
    }
    reminders.append(entry)
    save_memory(mem)
    return SkillResult.ok(reminder=entry, message=f"Rappel enregistré: {reminder_text}")
