"""Tests intent-based tool routing (Cursor-style)."""
from __future__ import annotations

from tool_router import select_tools_for_message

SAMPLE_TOOLS = [
    {"function": {"name": "web_search"}},
    {"function": {"name": "browser_open"}},
    {"function": {"name": "read_file"}},
    {"function": {"name": "emo_reflect"}},
]


def _names(tools):
    return [(t.get("function") or {}).get("name") for t in tools]


def test_tools_disabled_returns_empty():
    assert select_tools_for_message("ouvre google", SAMPLE_TOOLS, tools_enabled=False) == []


def test_openai_gets_all_tools():
    out = select_tools_for_message("hello", SAMPLE_TOOLS, provider="openai")
    assert len(out) == len(SAMPLE_TOOLS)


def test_web_intent_includes_browser():
    out = select_tools_for_message("cherche sur youtube des mods minecraft", SAMPLE_TOOLS, provider="groq")
    names = set(_names(out))
    assert "web_search" in names
    assert "browser_open" in names


def test_reflect_intent_for_owner():
    out = select_tools_for_message("réfléchis sur ton identité", SAMPLE_TOOLS, is_owner=True, provider="groq")
    names = set(_names(out))
    assert "emo_reflect" in names


def test_local_tools_when_agent_online_and_code_intent():
    out = select_tools_for_message("fix ce bug python", SAMPLE_TOOLS, agent_online=True, provider="groq")
    names = set(_names(out))
    assert "read_file" in names
