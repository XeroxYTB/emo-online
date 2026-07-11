"""Contrôle clavier/souris — PyAutoGUI optionnel."""
from __future__ import annotations

from typing import Any

from emo.desktop.actions._base import SkillResult

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False


def run(args: dict) -> Any:
    if not _HAS_PYAUTOGUI:
        return SkillResult.fail("Installez pyautogui pour le contrôle souris/clavier")
    action = (args.get("action") or "info").lower()
    query = (args.get("query") or "").lower()
    if "clic" in query or action == "click":
        x = int(args.get("x") or 100)
        y = int(args.get("y") or 100)
        pyautogui.click(x, y)
        return SkillResult.ok(action="click", x=x, y=y)
    if "tape" in query or action == "type":
        text = args.get("text") or args.get("query") or ""
        pyautogui.write(text, interval=0.02)
        return SkillResult.ok(action="type", chars=len(text))
    w, h = pyautogui.size()
    return SkillResult.ok(screen=f"{w}x{h}", message=f"Écran {w}×{h}")
