"""Traitement fichiers — conversion basique stub."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    path = args.get("path") or args.get("query") or ""
    p = Path(path).expanduser()
    if not p.is_file():
        return SkillResult.fail("Fichier requis")
    suffix = p.suffix.lower()
    if suffix == ".txt":
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        return SkillResult.ok(lines=len(lines), preview="\n".join(lines[:10]), message=f"{len(lines)} lignes")
    if suffix == ".json":
        import json
        data = json.loads(p.read_text(encoding="utf-8"))
        return SkillResult.ok(keys=list(data.keys()) if isinstance(data, dict) else type(data).__name__, message="JSON chargé")
    return SkillResult.ok(
        path=str(p),
        size=p.stat().st_size,
        message=f"Fichier {suffix or 'sans extension'} — traitement avancé Phase 2",
    )
