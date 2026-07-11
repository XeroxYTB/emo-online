"""Contrôle bureau — fenêtres stub."""
from __future__ import annotations

import subprocess
import sys
from typing import Any

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    if sys.platform != "win32":
        return SkillResult.fail("desktop_control: Windows Phase 1")
    query = (args.get("query") or "").lower()
    if "verrou" in query or "lock" in query:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        return SkillResult.ok(action="lock", message="Session verrouillée")
    if "bureau" in query or "desktop" in query:
        subprocess.Popen("explorer shell:Desktop", shell=True)
        return SkillResult.ok(action="show_desktop", message="Bureau affiché")
    return SkillResult.ok(message="desktop_control stub — précisez action (verrou, bureau)")
