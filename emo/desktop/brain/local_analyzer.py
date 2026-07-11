"""Analyse locale gratuite — AST, grep, listage fichiers."""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any


SKIP_DIRS = {".git", "node_modules", "__pycache__", "vendor", ".venv"}


def list_files(root: str | Path, pattern: str = "*", max_results: int = 200) -> dict[str, Any]:
    root_p = Path(root).expanduser().resolve()
    if not root_p.exists():
        return {"ok": False, "error": f"Chemin introuvable: {root_p}"}
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root_p):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
        for fname in filenames:
            if len(found) >= max_results:
                break
            if pattern == "*" or Path(fname).match(pattern):
                found.append(str(Path(dirpath) / fname))
        if len(found) >= max_results:
            break
    return {"ok": True, "files": found, "count": len(found), "root": str(root_p)}


def grep_files(
    root: str | Path,
    pattern: str,
    *,
    glob: str = "*",
    ignore_case: bool = True,
    max_results: int = 100,
) -> dict[str, Any]:
    root_p = Path(root).expanduser().resolve()
    if not pattern:
        return {"ok": False, "error": "pattern requis"}
    needle = pattern.lower() if ignore_case else pattern
    matches: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root_p):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
        for fname in filenames:
            if len(matches) >= max_results:
                break
            if glob != "*" and not Path(fname).match(glob):
                continue
            fp = Path(dirpath) / fname
            try:
                if fp.stat().st_size > 2_000_000:
                    continue
                with fp.open("r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        hay = line.lower() if ignore_case else line
                        if needle in hay:
                            matches.append({"file": str(fp), "line": i, "text": line.strip()[:300]})
                            if len(matches) >= max_results:
                                break
            except OSError:
                continue
        if len(matches) >= max_results:
            break
    return {"ok": True, "matches": matches, "count": len(matches)}


def ast_tree(file_path: str | Path) -> dict[str, Any]:
    p = Path(file_path).expanduser()
    if not p.is_file():
        return {"ok": False, "error": "fichier introuvable"}
    try:
        source = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(p))
    except SyntaxError as e:
        return {"ok": False, "error": f"syntaxe invalide: {e}"}
    except OSError as e:
        return {"ok": False, "error": str(e)}

    nodes: list[dict] = []

    class Visitor(ast.NodeVisitor):
        def generic_visit(self, node: ast.AST) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes.append({
                    "type": type(node).__name__,
                    "name": getattr(node, "name", ""),
                    "line": getattr(node, "lineno", 0),
                })
            super().generic_visit(node)

    Visitor().visit(tree)
    return {"ok": True, "file": str(p.resolve()), "nodes": nodes, "node_count": len(nodes)}


def analyze_project(root: str | Path, query: str = "") -> dict[str, Any]:
    """Analyse rapide d'un projet — fichiers Python + grep optionnel."""
    root_p = Path(root).expanduser()
    py_files = list_files(root_p, "*.py", max_results=100)
    result: dict[str, Any] = {
        "ok": True,
        "root": str(root_p.resolve()),
        "python_files": py_files.get("files", [])[:20],
    }
    if query:
        result["grep"] = grep_files(root_p, query, glob="*.py")
    trees = []
    for f in (py_files.get("files") or [])[:5]:
        t = ast_tree(f)
        if t.get("ok"):
            trees.append({"file": f, "nodes": t.get("nodes", [])})
    result["ast_samples"] = trees
    return result
