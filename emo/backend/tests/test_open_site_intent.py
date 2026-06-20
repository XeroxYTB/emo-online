"""Tests open-site intent detection."""
from __future__ import annotations

from open_site_intent import is_simple_open_request, resolve_open_site_url
from tool_router import select_tools_for_message

TOOLS = [
    {"function": {"name": "web_search"}},
    {"function": {"name": "browser_visit"}},
    {"function": {"name": "browser_open"}},
]


def _names(tools):
    return {(t.get("function") or {}).get("name") for t in tools}


def test_ouvres_ytb():
    assert resolve_open_site_url("ouvres ytb") == "https://www.youtube.com/"


def test_open_youtube():
    assert resolve_open_site_url("open youtube") == "https://www.youtube.com/"


def test_ouvre_google_com():
    url = resolve_open_site_url("ouvre google.com")
    assert url and "google.com" in url


def test_cherche_not_open():
    assert resolve_open_site_url("cherche des mods minecraft") is None


def test_simple_open_request():
    assert is_simple_open_request("ouvres ytb")
    assert not is_simple_open_request("ouvre ytb et cherche des tutos")


def test_open_intent_excludes_web_search():
    out = select_tools_for_message("ouvres ytb", TOOLS, provider="groq")
    names = _names(out)
    assert "browser_visit" in names
    assert "web_search" not in names
