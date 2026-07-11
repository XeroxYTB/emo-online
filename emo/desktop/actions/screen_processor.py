"""Capture écran — stub opencv/PIL optionnel."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from emo.desktop.actions._base import SkillResult

_OUT = Path(__file__).resolve().parent.parent / "data" / "screenshots"


def run(args: dict) -> Any:
    _OUT.mkdir(parents=True, exist_ok=True)
    dest = _OUT / f"screen_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
    try:
        import pyautogui
        img = pyautogui.screenshot()
        img.save(dest)
        return SkillResult.ok(path=str(dest), message=f"Capture: {dest.name}")
    except ImportError:
        return SkillResult.fail("Installez pyautogui pour les captures (opencv Phase 2)")
    except Exception as e:
        return SkillResult.fail(str(e))
