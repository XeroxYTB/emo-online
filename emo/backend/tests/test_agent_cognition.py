"""Tests cognition agent — think, todo, gates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_cognition import (
    check_planning_gate,
    require_think_before_act,
    default_cognition,
    _thought_covers_tool,
)


def test_planning_gate_blocks_write():
    cog = default_cognition(planning_required=True)
    err = check_planning_gate(cog, "write_file")
    assert err and err.get("planning_gate")


def test_planning_allows_think():
    cog = default_cognition(planning_required=True)
    assert check_planning_gate(cog, "emo_think") is None


def test_think_required_before_write():
    cog = default_cognition(planning_required=False)
    cog["planning_complete"] = True
    err = require_think_before_act(cog, "write_file")
    assert err and err.get("think_gate")


def test_thought_covers_tool():
    cog = default_cognition()
    cog["planning_complete"] = True
    cog["thoughts"] = [{"before_tool": "write_file", "ts": "2026-01-01T00:00:00+00:00"}]
    assert _thought_covers_tool(cog, "write_file")


def test_build_cognition_context_with_skeleton():
    from agent_cognition import build_cognition_context_prompt
    cog = default_cognition(planning_required=True)
    out = build_cognition_context_prompt(
        cog, content="Crée une API FastAPI complète avec auth JWT", mega=True,
    )
    assert "Plan suggéré" in out
    assert "emo_think" in out
