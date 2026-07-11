"""Base pour les skills Emo Desktop."""
from __future__ import annotations

from typing import Any


class SkillResult(dict):
    """Résultat standardisé d'un skill."""

    @classmethod
    def ok(cls, **kwargs: Any) -> "SkillResult":
        return cls({"ok": True, **kwargs})

    @classmethod
    def fail(cls, error: str, **kwargs: Any) -> "SkillResult":
        return cls({"ok": False, "error": error, **kwargs})


class BaseSkill:
    name: str = "base"
    description: str = ""

    def run(self, args: dict | None = None) -> Any:
        raise NotImplementedError
