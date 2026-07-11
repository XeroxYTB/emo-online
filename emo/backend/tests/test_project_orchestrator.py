"""Tests orchestrateur méga-projets."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from project_orchestrator import (
    SCOPE_MEGA,
    SCOPE_LARGE,
    classify_project_scope,
    infer_product_modules,
    build_initial_project_plan,
    is_continuation_request,
    resolve_project_mode,
)


def test_mega_launcher_request():
    msg = (
        "launcher minecraft COMPLET avec mod market gestion de comptes "
        "gestion d'instance"
    )
    assert classify_project_scope(msg) == SCOPE_MEGA
    mods = infer_product_modules(msg)
    ids = {m["id"] for m in mods}
    assert "auth" in ids
    assert "instances" in ids
    assert "mod_market" in ids


def test_large_without_mega():
    assert classify_project_scope("crée un mod fabric 1.20.1") == SCOPE_LARGE


def test_continuation_keeps_plan():
    plan = build_initial_project_plan("launcher complet", "/tmp/proj")
    large, mega, kept = resolve_project_mode("continue la phase suivante", plan)
    assert large and mega and kept is plan


def test_plan_has_phases():
    plan = build_initial_project_plan("plateforme SaaS complète avec auth et dashboard", "")
    assert len(plan["phases"]) >= 6
    assert plan["phases"][0]["status"] == "active"


def test_continuation_keywords():
    assert is_continuation_request("vas-y continue")
    assert not is_continuation_request("quelle heure est-il")
