"""Aide code — suggestions locales."""
from __future__ import annotations

from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.brain.local_analyzer import grep_files


def run(args: dict) -> Any:
    prompt = (args.get("prompt") or args.get("query") or "").strip()
    if not prompt:
        return SkillResult.fail("Question code requise")
    path = args.get("path") or "."
    hints = []
    if any(w in prompt.lower() for w in ("erreur", "bug", "fix", "traceback")):
        hints.append("Vérifiez les logs et lancez les tests unitaires.")
        hints.append("Utilisez local_analyzer pour grep/AST sur le projet.")
    if "python" in prompt.lower():
        hints.append("python -m pytest pour valider les changements.")
    grep_result = None
    for word in prompt.split():
        if len(word) > 4 and word.isidentifier():
            grep_result = grep_files(path, word, glob="*.py", max_results=10)
            break
    msg = "\n".join(hints) or f"Analyse code: {prompt[:80]}"
    return SkillResult.ok(hints=hints, grep=grep_result, message=msg)
