"""Tests changement de mode par commande vocale/texte."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.mode_switch import parse_mode_switch


def test_parse_mode_vocal():
    assert parse_mode_switch("passe en mode vocal") == "VOCAL"
    assert parse_mode_switch("active le vocal") == "VOCAL"
    assert parse_mode_switch("switch voix") == "VOCAL"


def test_parse_mode_agent():
    assert parse_mode_switch("mode agent") == "AGENT"
    assert parse_mode_switch("passe en mode outils") == "AGENT"


def test_parse_mode_chat():
    assert parse_mode_switch("retour au mode chat") == "CHAT"
    assert parse_mode_switch("quitte le vocal") == "CHAT"
    assert parse_mode_switch("arrête le mode agent") == "CHAT"


def test_parse_mode_status():
    assert parse_mode_switch("quel est le mode") == "STATUS"


def test_parse_mode_none():
    assert parse_mode_switch("salut comment ça va") is None
