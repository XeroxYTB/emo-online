"""Impression document — Windows print verb."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    path = args.get("path") or args.get("query") or ""
    p = Path(path).expanduser()
    if not p.is_file():
        return SkillResult.fail("Chemin fichier requis")
    if sys.platform != "win32":
        return SkillResult.fail("print_document: Windows Phase 1")
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f'Start-Process -FilePath "{p.resolve()}" -Verb Print'],
            check=False,
            capture_output=True,
        )
        return SkillResult.ok(path=str(p.resolve()), message=f"Impression lancée: {p.name}")
    except OSError as e:
        return SkillResult.fail(str(e))
