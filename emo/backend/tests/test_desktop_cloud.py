"""Tests cloud client + config desktop."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.config import DEFAULT_CONFIG
from emo.desktop.gemini_session import GeminiSession, _has_cloud_session, _is_quota_error


def test_default_backend_url_is_cloud():
    assert "hf.space" in DEFAULT_CONFIG["backend_url"]
    assert not DEFAULT_CONFIG["backend_url"].endswith("/api")


def test_normalize_backend_url_no_double_api():
    from emo.desktop.config import backend_api, backend_base

    assert backend_api("https://xroxx-emo-online-api.hf.space/api") == (
        "https://xroxx-emo-online-api.hf.space/api"
    )
    assert backend_api("https://xroxx-emo-online-api.hf.space") == (
        "https://xroxx-emo-online-api.hf.space/api"
    )
    assert backend_base("https://xroxx-emo-online-api.hf.space/api") == (
        "https://xroxx-emo-online-api.hf.space"
    )


def test_quota_error_detection():
    assert _is_quota_error(Exception("429 RESOURCE_EXHAUSTED"))
    assert _is_quota_error(Exception("quota exceeded for gemini-2.0-flash"))
    assert not _is_quota_error(Exception("connection refused"))


def test_has_cloud_session():
    with patch("emo.desktop.gemini_session.load_config", return_value={"session_token": "tok"}):
        assert _has_cloud_session()
    with patch("emo.desktop.gemini_session.load_config", return_value={"session_token": ""}):
        assert not _has_cloud_session()


def test_chat_prefers_cloud_when_paired():
    import asyncio

    session = GeminiSession()
    session._cloud = MagicMock()
    session._cloud.chat = AsyncMock(return_value="Salut depuis le cloud !")

    with patch("emo.desktop.gemini_session._has_cloud_session", return_value=True):
        out = asyncio.run(session.chat_text("salut"))
    assert out == "Salut depuis le cloud !"
    session._cloud.chat.assert_awaited_once_with("salut")


def test_chat_gemini_quota_falls_back_to_cloud():
    import asyncio

    session = GeminiSession()
    session._genai = MagicMock()
    session._genai.models.generate_content.side_effect = Exception("429 quota exceeded")
    session._cloud = MagicMock()
    session._cloud.chat = AsyncMock(return_value="Réponse cloud")

    with (
        patch("emo.desktop.gemini_session._has_cloud_session", return_value=False),
        patch.object(session, "_log"),
    ):
        out = asyncio.run(session.chat_text("hello"))
    assert out == "Réponse cloud"
    assert session.quota_exhausted


def test_voice_session_uses_cloud_stt_when_paired():
    session = GeminiSession()
    session._genai = MagicMock()
    with patch("emo.desktop.gemini_session._has_cloud_session", return_value=True):
        r = session.start_voice_session()
    assert r["ok"] is True
    assert r["mode"] == "cloud_hybrid"
