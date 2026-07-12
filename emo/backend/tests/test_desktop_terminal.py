"""Tests mode terminal Emo Desktop."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.cli.terminal import TerminalApp, _has_chat_config, run_terminal


def test_has_chat_config_requires_key_or_token():
    assert _has_chat_config({"gemini_api_key": "k", "session_token": ""})
    assert _has_chat_config({"gemini_api_key": "", "session_token": "tok"})
    assert not _has_chat_config({"gemini_api_key": "", "session_token": ""})


def test_terminal_once_mocked_chat(capsys):
    cfg = {"gemini_api_key": "", "session_token": "tok"}
    mock_session = MagicMock()
    mock_session.chat_text = AsyncMock(return_value="Salut depuis le cloud !")

    with (
        patch("emo.desktop.cli.terminal.load_config", return_value=cfg),
        patch("emo.desktop.cli.terminal.GeminiSession", return_value=mock_session),
        patch("emo.desktop.cli.terminal.EmoLiveSession"),
        patch("emo.desktop.cli.terminal.EmoSpeechEngine"),
    ):
        code = run_terminal(["--terminal", "--once", "--text", "bonjour", "--no-mic"])

    assert code == 0
    out = capsys.readouterr().out
    assert "Vous: bonjour" in out
    assert "Émo: Salut depuis le cloud !" in out
    mock_session.chat_text.assert_awaited_once_with("bonjour")


def test_terminal_missing_config_exits_one(capsys):
    with patch("emo.desktop.cli.terminal.load_config", return_value={"gemini_api_key": "", "session_token": ""}):
        code = run_terminal(["--terminal", "--once", "--text", "hi", "--no-mic"])
    assert code == 1
    assert "ERR:" in capsys.readouterr().err


def test_terminal_process_text_mode_switch(capsys):
    cfg = {"gemini_api_key": "key", "session_token": ""}
    with (
        patch("emo.desktop.cli.terminal.load_config", return_value=cfg),
        patch("emo.desktop.cli.terminal.GeminiSession"),
        patch("emo.desktop.cli.terminal.EmoLiveSession"),
        patch("emo.desktop.cli.terminal.EmoSpeechEngine"),
    ):
        app = TerminalApp(no_mic=True, no_tts=True)
        app.process_text("passe en mode vocal", speak=False)
        app.shutdown()

    out = capsys.readouterr().out
    assert "Vous: passe en mode vocal" in out
    assert "Mode VOCAL" in out
    assert app._mode == "VOCAL"


def test_terminal_once_without_text_fails():
    cfg = {"gemini_api_key": "k", "session_token": ""}
    with (
        patch("emo.desktop.cli.terminal.load_config", return_value=cfg),
        patch("emo.desktop.cli.terminal.GeminiSession"),
        patch("emo.desktop.cli.terminal.EmoLiveSession"),
        patch("emo.desktop.cli.terminal.EmoSpeechEngine"),
    ):
        code = run_terminal(["--terminal", "--once", "--no-mic"])
    assert code == 1
