"""Tests du package emo.desktop (skills + router)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.actions.skill_loader import EXPECTED_SKILLS, list_skills, run_skill
from emo.desktop.task_router import route_message


def test_all_24_skills_registered():
    found = set(list_skills())
    missing = [s for s in EXPECTED_SKILLS if s not in found]
    assert not missing, f"Skills manquants: {missing}"
    assert len(found) >= 24


def test_task_router_web_search():
    r = route_message("cherche les actualités sur l'IA")
    assert r.action in ("run_skill", "respond")
    if r.action == "run_skill":
        assert r.skill == "web_search"


def test_file_controller_list():
    res = run_skill("file_controller", {"action": "list", "path": "."})
    assert res.get("ok") is True
