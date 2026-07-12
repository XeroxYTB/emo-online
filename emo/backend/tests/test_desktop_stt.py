"""Tests STT + dashboard URL (Emo Desktop)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.dashboard.server import dashboard_local_url
from emo.desktop.stt import (
    EmoSTTEngine,
    _clean_transcript,
    _has_cloud_session,
    _is_quota_error,
)


def test_dashboard_local_url_uses_loopback():
    assert dashboard_local_url(8000) == "http://127.0.0.1:8000/pair"
    assert "0.0.0.0" not in dashboard_local_url(9000, "/pair")


def test_clean_transcript_strips_ctrl_tokens():
    assert _clean_transcript("  bonjour <ctrl95>  ") == "bonjour"


def test_quota_error_detection():
    assert _is_quota_error(Exception("429 RESOURCE_EXHAUSTED"))
    assert not _is_quota_error(Exception("connection reset"))


def test_stt_prefers_local_when_flag_set():
    engine = EmoSTTEngine(prefer_local=True, on_log=MagicMock())
    engine._active = True
    with patch.object(engine, "_fallback_loop", return_value=None) as fb:
        import asyncio

        asyncio.run(engine._run())
        fb.assert_awaited_once()


def test_stt_skips_gemini_on_quota_in_loop():
    engine = EmoSTTEngine(on_log=MagicMock())
    engine._active = True
    mock_client = MagicMock()
    mock_client.aio.live.connect.side_effect = Exception("429 quota exceeded")
    with (
        patch("emo.desktop.stt._get_api_key", return_value="fake-key"),
        patch("emo.desktop.stt._has_cloud_session", return_value=False),
        patch("google.genai.Client", return_value=mock_client),
        patch.object(engine, "_fallback_loop", return_value=None) as fb,
    ):
        import asyncio

        asyncio.run(engine._run())
        fb.assert_awaited_once()


def test_stt_auto_prefers_local_when_cloud_paired():
    with patch("emo.desktop.stt._has_cloud_session", return_value=True):
        engine = EmoSTTEngine(on_log=MagicMock())
    assert engine.prefer_local is True


def test_stt_uses_google_not_sapi():
    engine = EmoSTTEngine(on_log=MagicMock())
    r = MagicMock()
    r.recognize_google.return_value = "bonjour"
    audio = MagicMock()
    out = engine._recognize_audio(r, audio)
    assert out == "bonjour"
    r.recognize_google.assert_called_once_with(audio, language="fr-FR")
    assert not hasattr(engine, "_recognize_windows_sapi")


def test_stt_mic_paused_during_speaking():
    engine = EmoSTTEngine(
        is_speaking=lambda: True,
        on_log=MagicMock(),
    )
    assert engine._mic_paused() is True


def test_stt_mic_resumes_after_echo_cooldown():
    engine = EmoSTTEngine(
        is_speaking=lambda: False,
        on_log=MagicMock(),
    )
    engine._last_speaking_end = 0.0
    assert engine._mic_paused() is False


def test_has_cloud_session():
    with patch("emo.desktop.stt.load_config", return_value={"session_token": "abc"}):
        assert _has_cloud_session() is True
    with patch("emo.desktop.stt.load_config", return_value={}):
        assert _has_cloud_session() is False
