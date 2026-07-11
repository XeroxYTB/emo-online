"""Tests STT + dashboard URL (Emo Desktop)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.dashboard.server import dashboard_local_url
from emo.desktop.stt import EmoSTTEngine, _clean_transcript, _is_quota_error


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
        patch("google.genai.Client", return_value=mock_client),
        patch.object(engine, "_fallback_loop", return_value=None) as fb,
    ):
        import asyncio

        asyncio.run(engine._run())
        fb.assert_awaited_once()
