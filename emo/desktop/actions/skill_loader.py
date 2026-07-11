"""Chargement dynamique des 24 skills."""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Callable

from emo.desktop.actions import _base

_SKILLS: dict[str, Callable[[dict], Any]] = {}
_LOADED = False

# Fichiers skill attendus (sans .py)
EXPECTED_SKILLS = [
    "open_app",
    "web_search",
    "weather_report",
    "send_message",
    "reminder",
    "youtube_video",
    "computer_settings",
    "computer_control",
    "browser_control",
    "file_controller",
    "file_processor",
    "code_helper",
    "dev_agent_skill",
    "desktop_control",
    "game_updater",
    "flight_finder",
    "print_document",
    "run_python_script",
    "fallback_agent",
    "local_analyzer_skill",
    "agent_actions",
    "screen_processor",
    "system_monitor_skill",
    "proactive",
]


def _discover_skills() -> None:
    global _LOADED
    if _LOADED:
        return
    package = importlib.import_module("emo.desktop.actions")
    prefix = package.__name__ + "."
    for modinfo in pkgutil.iter_modules(package.__path__, prefix):
        name = modinfo.name.split(".")[-1]
        if name.startswith("_") or name in ("skill_loader",):
            continue
        try:
            mod = importlib.import_module(modinfo.name)
            fn = getattr(mod, "run", None) or getattr(mod, "run_skill", None)
            if callable(fn):
                _SKILLS[name] = fn
        except Exception:
            pass
    _LOADED = True


def list_skills() -> list[str]:
    _discover_skills()
    return sorted(_SKILLS.keys())


def run_skill(name: str, args: dict | None = None) -> Any:
    _discover_skills()
    fn = _SKILLS.get(name)
    if fn is None:
        return _base.SkillResult.fail(f"Skill inconnu: {name}")
    try:
        return fn(args or {})
    except Exception as e:
        return _base.SkillResult.fail(str(e))


def skill_count() -> int:
    _discover_skills()
    return len(_SKILLS)
