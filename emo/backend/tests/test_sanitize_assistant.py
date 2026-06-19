"""Sanitize assistant text — mood tags and LLM artefacts."""
from server import _sanitize_assistant_text


def test_sanitize_tool_and_mood_leak():
    raw = (
        'SltÉmoNEUTRE<function(web_search){"query": "bonjour", "limit": "5"}</function>'
        "<MOOD:curieuse> On va essayer de casser ce cercle !"
    )
    clean, mood = _sanitize_assistant_text(raw)
    assert mood == "curieuse"
    assert "function" not in clean.lower()
    assert "MOOD" not in clean
    assert clean.startswith("On va essayer")


def test_sanitize_github_search_leak():
    raw = (
        '<function(github_search){"query": "exemple de projet", "limit": "3"}</function>'
        "<MOOD:ironique> Tu es décidément très créatif dans tes salutations !"
    )
    clean, mood = _sanitize_assistant_text(raw)
    assert mood == "ironique"
    assert "function" not in clean.lower()
    assert "MOOD" not in clean
    assert clean.startswith("Tu es décidément")


def test_sanitize_bracket_mood_at_end():
    clean, mood = _sanitize_assistant_text("Salut Hugo !\n[MOOD:curieuse]")
    assert mood == "curieuse"
    assert clean == "Salut Hugo !"
