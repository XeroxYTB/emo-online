"""
Deprecated — EmoVoiceEngine remplacé par EmoLiveSession + repli STT/TTS explicite.

Utilisez:
  - emo.desktop.core.live_session.EmoLiveSession (Gemini Live Mark-XLVIII)
  - emo.desktop.stt.EmoSTTEngine (repli local)
  - emo.desktop.tts.EmoSpeechEngine (repli local)
"""
from __future__ import annotations

import warnings

from emo.desktop.core.live_session import EmoLiveSession

warnings.warn(
    "emo.desktop.voice_engine.EmoVoiceEngine est déprécié — utilisez EmoLiveSession",
    DeprecationWarning,
    stacklevel=2,
)


class EmoVoiceEngine(EmoLiveSession):
    """Alias rétrocompatible — délègue à EmoLiveSession."""

    def __init__(self, *args, on_user_text=None, on_assistant_text=None, on_speaking=None, **kwargs):
        kwargs.setdefault("on_user_speech", on_user_text)
        kwargs.setdefault("on_assistant_speech", on_assistant_text)
        if on_speaking:
            kwargs.setdefault("on_state", lambda s: on_speaking(s == "SPEAKING"))
        super().__init__(*args, **kwargs)
