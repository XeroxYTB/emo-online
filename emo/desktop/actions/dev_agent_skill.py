"""Skill wrapper pour dev_agent."""
from __future__ import annotations

from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.brain.dev_agent import DevAgent


def run(args: dict) -> Any:
    prompt = (args.get("prompt") or args.get("query") or "").strip()
    if not prompt:
        return SkillResult.fail("Description du projet requise")
    agent = DevAgent()
    result = agent.develop(prompt)
    if not result.get("ok"):
        return SkillResult.fail(result.get("run", {}).get("error", "échec dev"), **result)
    return SkillResult.ok(**result, message=f"Projet dans {result.get('workspace')}")
