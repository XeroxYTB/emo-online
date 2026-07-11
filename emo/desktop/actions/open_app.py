"""Ouvre des applications Windows courantes."""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from emo.desktop.actions._base import SkillResult

APPS = {
    "notepad": "notepad",
    "bloc": "notepad",
    "notes": "notepad",
    "calc": "calc",
    "calculatrice": "calc",
    "calculator": "calc",
    "explorer": "explorer",
    "explorateur": "explorer",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": "msedge",
    "firefox": "firefox",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "vscode": "code",
    "code": "code",
}


def _resolve_app(query: str) -> str | None:
    low = query.lower()
    for key, cmd in APPS.items():
        if key in low:
            return cmd
    return None


def run(args: dict) -> Any:
    query = (args.get("query") or args.get("prompt") or args.get("app") or "").strip()
    if not query:
        return SkillResult.fail("Nom d'application requis")
    cmd = _resolve_app(query)
    if not cmd:
        # Dernier recours: start avec le texte brut
        cmd = query.split()[-1] if " " in query else query

    if sys.platform != "win32":
        return SkillResult.fail("open_app optimisé pour Windows")

    try:
        if os.path.isfile(cmd):
            subprocess.Popen([cmd], shell=False)
        else:
            subprocess.Popen(f'start "" {cmd}', shell=True)
        return SkillResult.ok(app=cmd, message=f"Application lancée: {cmd}")
    except OSError as e:
        return SkillResult.fail(str(e))
