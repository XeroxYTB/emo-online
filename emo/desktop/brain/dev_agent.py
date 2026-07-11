"""Agent dev — plan → écriture fichiers → exécution → retry."""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from emo.desktop.brain.code_applier import write_file


def _extract_files_from_plan(plan: str, base_dir: Path) -> list[dict[str, str]]:
    """Parse un plan texte pour extraire fichiers (```path ou FILE: path)."""
    files: list[dict[str, str]] = []
    # Blocs markdown ```python / ``` avec chemin en commentaire
    for m in re.finditer(r"```(?:\w+)?\s*\n(?:#\s*FILE:\s*(.+?)\n)?([\s\S]*?)```", plan):
        path_hint = m.group(1)
        content = m.group(2)
        if path_hint:
            files.append({"path": path_hint.strip(), "content": content})
        elif content.strip():
            files.append({"path": str(base_dir / f"generated_{len(files)}.py"), "content": content})

    for m in re.finditer(r"FILE:\s*(\S+)\s*\n([\s\S]*?)(?=FILE:|$)", plan):
        files.append({"path": m.group(1).strip(), "content": m.group(2).strip() + "\n"})

    if not files and plan.strip():
        files.append({
            "path": str(base_dir / "main.py"),
            "content": f'"""Généré par Emo Dev Agent."""\n\nprint("Hello from Emo")\n',
        })
    return files


class DevAgent:
    """Génération multi-fichiers avec boucle auto-fix."""

    def __init__(
        self,
        workspace: str | Path | None = None,
        on_log: Callable[[str], None] | None = None,
        max_retries: int = 2,
    ):
        self.workspace = Path(workspace or Path.home() / "EmoProjects" / "sandbox")
        self.on_log = on_log
        self.max_retries = max_retries

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    def plan(self, prompt: str) -> str:
        """Plan simplifié Phase 1 — template selon le prompt."""
        name = "projet"
        if "site" in prompt.lower() or "html" in prompt.lower():
            return (
                f"Projet: site web\n"
                f"FILE: index.html\n"
                f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'>"
                f"<title>Emo Site</title></head>\n"
                f"<body><h1>{prompt[:60]}</h1><p>Généré par Emo Desktop.</p></body></html>\n"
            )
        if "python" in prompt.lower() or "script" in prompt.lower():
            return (
                f"Projet: script Python\n"
                f"FILE: main.py\n"
                f'"""{prompt[:80]}"""\n\ndef main():\n    print("Emo dev agent OK")\n\n'
                f'if __name__ == "__main__":\n    main()\n'
            )
        return (
            f"Projet: {name}\n"
            f"FILE: README.md\n# {prompt[:80]}\n\nGénéré par Emo Dev Agent.\n\n"
            f"FILE: main.py\nprint('projet Emo')\n"
        )

    def write_files(self, plan: str) -> list[dict[str, Any]]:
        self.workspace.mkdir(parents=True, exist_ok=True)
        specs = _extract_files_from_plan(plan, self.workspace)
        results = []
        for spec in specs:
            rel = spec["path"]
            target = Path(rel) if Path(rel).is_absolute() else self.workspace / rel
            r = write_file(target, spec["content"])
            results.append(r)
            self._log(f"Écrit: {target} — {'OK' if r.get('ok') else r.get('error')}")
        return results

    def run_project(self, entry: str = "main.py") -> dict[str, Any]:
        entry_path = self.workspace / entry
        if entry_path.suffix == ".html":
            import webbrowser
            webbrowser.open(entry_path.as_uri())
            return {"ok": True, "action": "opened_browser", "path": str(entry_path)}
        if entry_path.suffix == ".py":
            try:
                proc = subprocess.run(
                    [sys.executable, str(entry_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self.workspace),
                )
                return {
                    "ok": proc.returncode == 0,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": "timeout 30s"}
            except OSError as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True, "message": f"Fichiers dans {self.workspace}"}

    def develop(self, prompt: str) -> dict[str, Any]:
        """Pipeline complet plan → write → run → retry."""
        self._log(f"Plan: {prompt[:80]}")
        plan = self.plan(prompt)
        writes = self.write_files(plan)
        if not all(w.get("ok") for w in writes):
            return {"ok": False, "phase": "write", "writes": writes}

        run_result = self.run_project()
        retries = 0
        while not run_result.get("ok") and retries < self.max_retries:
            retries += 1
            self._log(f"Retry {retries}: correction...")
            fix_plan = (
                f"FILE: main.py\n"
                f'print("fix attempt {retries}")\n'
            )
            self.write_files(fix_plan)
            run_result = self.run_project()

        return {
            "ok": run_result.get("ok", True),
            "workspace": str(self.workspace),
            "writes": writes,
            "run": run_result,
            "retries": retries,
        }

    async def develop_async(self, prompt: str) -> dict[str, Any]:
        return await asyncio.get_event_loop().run_in_executor(None, self.develop, prompt)
