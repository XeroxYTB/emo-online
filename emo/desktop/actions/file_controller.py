"""Opérations fichiers complètes via pathlib."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from emo.desktop.actions._base import SkillResult

SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def list_dir(path: str | Path, depth: int = 1) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"ok": False, "error": "chemin introuvable"}
    if not p.is_dir():
        return {"ok": False, "error": "pas un dossier"}
    if depth <= 1:
        files, dirs = [], []
        for entry in sorted(p.iterdir()):
            if entry.name.startswith("."):
                continue
            (dirs if entry.is_dir() else files).append(entry.name)
        return {"ok": True, "path": str(p.resolve()), "files": files, "dirs": dirs}
    entries = []
    root = p.resolve()

    def walk(d: Path, lvl: int):
        if lvl > depth or len(entries) >= 300:
            return
        try:
            items = sorted(d.iterdir())
        except OSError:
            return
        for entry in items:
            if entry.name.startswith("."):
                continue
            rel = entry.relative_to(root).as_posix()
            entries.append({"path": rel, "is_dir": entry.is_dir()})
            if entry.is_dir() and lvl < depth and entry.name not in SKIP_DIRS:
                walk(entry, lvl + 1)

    walk(p, 1)
    return {"ok": True, "path": str(root), "entries": entries}


def read_file(path: str | Path, offset: int = 1, limit: int = 0) -> dict:
    p = Path(path).expanduser()
    if not p.is_file():
        return {"ok": False, "error": "fichier introuvable"}
    content = p.read_text(encoding="utf-8", errors="replace")
    if offset > 1 or limit > 0:
        lines = content.splitlines()
        start = max(0, offset - 1)
        end = len(lines) if limit <= 0 else min(len(lines), start + limit)
        content = "\n".join(lines[start:end])
    return {"ok": True, "path": str(p.resolve()), "content": content}


def write_file(path: str | Path, content: str) -> dict:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(p.resolve()), "bytes": len(content.encode())}


def delete_path(path: str | Path) -> dict:
    p = Path(path).expanduser()
    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink(missing_ok=False)
    return {"ok": True, "deleted": str(p)}


def move_path(src: str | Path, dst: str | Path) -> dict:
    s, d = Path(src).expanduser(), Path(dst).expanduser()
    d.parent.mkdir(parents=True, exist_ok=True)
    s.rename(d)
    return {"ok": True, "from": str(s), "to": str(d.resolve())}


def find_files(root: str | Path, pattern: str, max_results: int = 100) -> dict:
    root_p = Path(root).expanduser()
    found = []
    for dirpath, dirnames, filenames in os.walk(root_p):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
        for fname in filenames:
            if len(found) >= max_results:
                break
            if "*" in pattern:
                if Path(fname).match(pattern):
                    found.append(str(Path(dirpath) / fname))
            elif pattern.lower() in fname.lower():
                found.append(str(Path(dirpath) / fname))
    return {"ok": True, "files": found, "count": len(found)}


def run(args: dict) -> Any:
    action = (args.get("action") or "list").lower()
    path = args.get("path") or args.get("query") or "."

    # Détection depuis texte naturel
    q = (args.get("query") or "").lower()
    if "liste" in q or "list" in q or "dossier" in q:
        action = "list"

    if action == "list":
        r = list_dir(path)
    elif action == "read":
        r = read_file(path, int(args.get("offset") or 1), int(args.get("limit") or 0))
    elif action == "write":
        content = args.get("content")
        if content is None:
            return SkillResult.fail("content requis pour write")
        r = write_file(path, content)
    elif action == "delete":
        r = delete_path(path)
    elif action == "move":
        r = move_path(args.get("from") or path, args.get("to") or "")
    elif action == "find":
        r = find_files(path, args.get("pattern") or "*")
    else:
        r = list_dir(path)

    if not r.get("ok"):
        return SkillResult.fail(r.get("error", "erreur"))
    if "entries" in r:
        msg = f"{len(r['entries'])} entrées dans {r['path']}"
    elif "files" in r and "dirs" in r:
        msg = f"{len(r['files'])} fichiers, {len(r['dirs'])} dossiers"
    elif "content" in r:
        msg = f"Lu {len(r['content'])} caractères"
    else:
        msg = "OK"
    return SkillResult.ok(**r, message=msg)
