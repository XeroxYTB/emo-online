"""Actions agent génériques."""
from __future__ import annotations

from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.actions.skill_loader import list_skills, run_skill


def run(args: dict) -> Any:
    tool = (args.get("tool") or args.get("skill") or "").strip()
    if tool:
        return run_skill(tool, args)
    return SkillResult.ok(
        tools=list_skills(),
        message="Spécifiez tool=<skill_name> ou utilisez le routeur.",
    )
