"""Tests cloud client + config desktop."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.config import DEFAULT_CONFIG
from emo.desktop.gemini_session import _is_quota_error


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
