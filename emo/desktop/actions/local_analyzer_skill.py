"""Skill analyse locale AST/grep."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.brain import local_analyzer as la


def run(args: dict) -> Any:
    query = (args.get("query") or args.get("pattern") or "").strip()
    path = args.get("path") or "."
    action = (args.get("action") or "project").lower()

    if action == "ast" and args.get("file"):
        r = la.ast_tree(args["file"])
    elif action == "grep" or query:
        r = la.grep_files(path, query or args.get("pattern", ""), glob=args.get("glob") or "*")
    elif action == "list":
        r = la.list_files(path, args.get("pattern") or "*")
    else:
        r = la.analyze_project(path, query)

    if not r.get("ok"):
        return SkillResult.fail(r.get("error", "erreur analyse"))
    if "matches" in r:
        msg = f"{r.get('count', 0)} correspondances"
    elif "files" in r:
        msg = f"{len(r['files'])} fichiers"
    elif "nodes" in r:
        msg = f"{r.get('node_count', 0)} nœuds AST"
    else:
        msg = f"Analyse {Path(path).name}"
    return SkillResult.ok(**r, message=msg)
