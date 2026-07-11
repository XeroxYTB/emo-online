"""Agent de repli — liste capacités."""
from __future__ import annotations

from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.actions.skill_loader import EXPECTED_SKILLS, list_skills


def run(args: dict) -> Any:
    loaded = list_skills()
    msg = (
        f"Emo Desktop — {len(loaded)} skills chargés.\n"
        "Modes: CHAT, VOCAL, AGENT.\n"
        "Exemples: « cherche … », « ouvre notepad », « météo Paris », « liste dossier ».\n"
        "Configurez gemini_api_key et agent_token dans Paramètres."
    )
    return SkillResult.ok(skills=loaded, expected=len(EXPECTED_SKILLS), message=msg)
