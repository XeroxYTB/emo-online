"""Tests aléatoires mode terminal — skills + router sans PyQt6."""
from __future__ import annotations

import random
import sys

from emo.desktop.actions.skill_loader import list_skills, run_skill
from emo.desktop.core.memory_manager import load_memory, update_memory
from emo.desktop.core.tool_declarations import get_tool_declarations
from emo.desktop.task_router import route_message

_RANDOM_PROMPTS = [
    "cherche les actualités IA",
    "météo à Paris",
    "ouvre notepad",
    "liste les fichiers du dossier courant",
    "analyse le projet",
    "salut emo",
    "passe en mode vocal",
    "quelle heure est-il",
    "aide moi",
    "cpu et ram",
]


def run_random_suite(n: int = 8, seed: int | None = None) -> int:
    rng = random.Random(seed)
    fails = 0
    print("=== Emo test suite (terminal) ===")
    print(f"Skills enregistrés: {len(list_skills())}")
    print(f"Outils Live déclarés: {len(get_tool_declarations())}")
    mem = load_memory()
    print(f"Mémoire: {sum(len(v) for v in mem.values() if isinstance(v, dict))} entrées")

    for i in range(n):
        prompt = rng.choice(_RANDOM_PROMPTS)
        route = route_message(prompt)
        print(f"\n[{i+1}/{n}] «{prompt}» -> {route.action} {route.skill or ''} ({route.reason})")
        if route.action == "run_skill" and route.skill:
            try:
                res = run_skill(route.skill, route.args or {"query": prompt})
                ok = True
                if isinstance(res, dict):
                    ok = res.get("ok", True) is not False
                print(f"  skill OK: {str(res)[:120]}")
                if not ok:
                    fails += 1
            except Exception as e:
                print(f"  skill FAIL: {e}")
                fails += 1
        elif route.action == "respond":
            print("  -> conversation (cloud/live)")
        else:
            print(f"  -> {route.action}")

    update_memory({"notes": {"test_suite": {"value": "ok"}}})
    print(f"\n=== Terminé: {n - fails}/{n} OK ===")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    sys.exit(run_random_suite(n))
