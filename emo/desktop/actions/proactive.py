"""Suggestions proactives basées sur mémoire."""
from __future__ import annotations

from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.memory import load_memory


def run(args: dict) -> Any:
    mem = load_memory()
    prefs = mem.get("preferences") or {}
    facts = mem.get("facts") or []
    suggestions = [
        "Configurez gemini_api_key pour le mode vocal.",
        "Connectez l'agent cloud via agent_token pour piloter le PC à distance.",
    ]
    if not prefs.get("dashboard_seen"):
        suggestions.insert(0, "Dashboard mobile sur http://127.0.0.1:8000/pair")
    if facts:
        suggestions.append(f"Dernier fait mémorisé: {facts[-1].get('text', '')[:60]}")
    return SkillResult.ok(suggestions=suggestions, message="\n".join(f"• {s}" for s in suggestions))
