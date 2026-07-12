"""Tests TTS fallback (Emo Desktop)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.desktop.tts import _is_live_unavailable_error


def test_live_unavailable_detects_1011():
    assert _is_live_unavailable_error(Exception("1011 None. The service is currently unavailable."))


def test_live_unavailable_detects_quota():
    assert _is_live_unavailable_error(Exception("429 RESOURCE_EXHAUSTED"))


def test_live_unavailable_ignores_generic():
    assert not _is_live_unavailable_error(Exception("connection reset"))
