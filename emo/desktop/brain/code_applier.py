"""Application de diffs / remplacements sur fichiers."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def apply_replacement(
    path: str | Path,
    old: str,
    new: str,
    *,
    replace_all: bool = False,
) -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.is_file():
        return {"ok": False, "error": "fichier introuvable"}
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        count = content.count(old)
        if count == 0:
            return {"ok": False, "error": "old_string introuvable"}
        if not replace_all and count > 1:
            return {"ok": False, "error": f"{count} occurrences — précisez ou replace_all=true"}
        updated = content.replace(old, new) if replace_all else content.replace(old, new, 1)
        p.write_text(updated, encoding="utf-8")
        return {"ok": True, "path": str(p.resolve()), "replacements": count if replace_all else 1}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def apply_unified_diff(path: str | Path, diff_text: str) -> dict[str, Any]:
    """Applique un diff unified simplifié (lignes + / -)."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {"ok": False, "error": "fichier introuvable"}
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError as e:
        return {"ok": False, "error": str(e)}

    new_lines: list[str] = []
    idx = 0
    applied = 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++") or raw.startswith("---") or raw.startswith("@@"):
            continue
        if raw.startswith("+"):
            new_lines.append(raw[1:] + ("\n" if not raw[1:].endswith("\n") else ""))
            applied += 1
        elif raw.startswith("-"):
            if idx < len(lines) and lines[idx].rstrip("\n") == raw[1:].rstrip("\n"):
                idx += 1
                applied += 1
            else:
                return {"ok": False, "error": f"ligne à supprimer non trouvée: {raw[1:][:60]}"}
        else:
            if idx < len(lines):
                new_lines.append(lines[idx])
                idx += 1
            elif raw.startswith(" "):
                new_lines.append(raw[1:] + "\n")

    while idx < len(lines):
        new_lines.append(lines[idx])
        idx += 1

    try:
        p.write_text("".join(new_lines), encoding="utf-8")
        return {"ok": True, "path": str(p.resolve()), "applied": applied}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def write_file(path: str | Path, content: str) -> dict[str, Any]:
    p = Path(path).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(p.resolve()), "bytes": len(content.encode())}
    except OSError as e:
        return {"ok": False, "error": str(e)}
