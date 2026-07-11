"""Exécute un script Python local."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    path = args.get("path") or args.get("script") or ""
    if not path:
        q = (args.get("query") or "")
        for word in q.split():
            if word.endswith(".py"):
                path = word
                break
    p = Path(path).expanduser()
    if not p.is_file():
        return SkillResult.fail(f"Script introuvable: {path}")
    try:
        proc = subprocess.run(
            [sys.executable, str(p)],
            capture_output=True,
            text=True,
            timeout=int(args.get("timeout") or 60),
            cwd=str(p.parent),
        )
        return SkillResult.ok(
            exit_code=proc.returncode,
            stdout=proc.stdout[:4000],
            stderr=proc.stderr[:2000],
            message=proc.stdout[:500] or proc.stderr[:200] or f"exit {proc.returncode}",
        )
    except subprocess.TimeoutExpired:
        return SkillResult.fail("timeout")
    except OSError as e:
        return SkillResult.fail(str(e))
