"""Tests outils Gemini Live (Emo Desktop)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_fc(name: str, args: dict, fc_id: str = "fc-1"):
    return SimpleNamespace(id=fc_id, name=name, args=args)


async def _run_tool(name: str, args: dict):
    from emo.desktop.core.tool_executor import execute_tool

    fc = _make_fc(name, args)
    return await execute_tool(
        fc,
        on_log=MagicMock(),
        on_state=MagicMock(),
        agent_folder="",
        current_file="",
    )


def test_save_memory_updates_store():
    import asyncio

    with patch("emo.desktop.core.tool_executor.update_memory") as upd:
        fr = asyncio.run(_run_tool("save_memory", {
            "category": "identity",
            "key": "name",
            "value": "Alice",
        }))
        upd.assert_called_once_with({"identity": {"name": {"value": "Alice"}}})
        assert fr.response["result"] == "ok"
        assert fr.response["silent"] is True


def test_open_app_maps_app_name_to_query():
    import asyncio

    with patch("emo.desktop.core.tool_executor.run_skill") as rs:
        rs.return_value = {"ok": True, "message": "Application lancée: notepad"}
        fr = asyncio.run(_run_tool("open_app", {"app_name": "Notepad"}))
        rs.assert_called_once()
        skill_name, skill_args = rs.call_args[0]
        assert skill_name == "open_app"
        assert skill_args["query"] == "Notepad"
        assert fr.response["result"]


def test_get_tool_declarations_includes_renamed_tools():
    from emo.desktop.core.tool_declarations import get_tool_declarations

    names = {d["name"] for d in get_tool_declarations()}
    assert "system_monitor_skill" in names
    assert "screen_processor" in names
    assert "dev_agent_skill" in names
    assert "run_custom_skill" in names
    assert "system_status" not in names
    assert "screen_process" not in names
    assert "dev_agent" not in names


def test_memory_manager_format_prompt():
    from emo.desktop.core.memory_manager import format_memory_for_prompt

    mem = {
        "identity": {"name": {"value": "Bob", "updated": "2026-01-01"}},
        "preferences": {},
        "projects": {},
        "relationships": {},
        "wishes": {},
        "notes": {},
    }
    text = format_memory_for_prompt(mem)
    assert "Bob" in text
    assert "WHAT YOU KNOW" in text
