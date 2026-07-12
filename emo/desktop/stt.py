"""Reconnaissance vocale — sounddevice + VAD + Google Speech (sans SAPI Windows)."""
from __future__ import annotations

import asyncio
import re
import threading
import time
from typing import Callable

from emo.desktop.config import load_config

SEND_SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
_DEFAULT_LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
_MAX_GEMINI_RETRIES = 1
_ENERGY_THRESHOLD = 150.0
_SILENCE_SEC = 0.75
_MAX_UTTERANCE_SEC = 14.0
_ECHO_COOLDOWN_SEC = 1.0

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


def _clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()


def _get_live_model() -> str:
    return (load_config().get("gemini_live_model") or _DEFAULT_LIVE_MODEL).strip()


def _get_api_key() -> str:
    return (load_config().get("gemini_api_key") or "").strip()


def _has_cloud_session() -> bool:
    return bool((load_config().get("session_token") or "").strip())


def _is_quota_error(exc: BaseException) -> bool:
    err = str(exc).lower()
    return any(k in err for k in ("429", "resource_exhausted", "quota", "rate limit"))


class _UseLocalSTT(Exception):
    """Bascule vers reconnaissance locale."""


class EmoSTTEngine:
    """Écoute micro en mode VOCAL et émet des transcriptions finales."""

    def __init__(
        self,
        on_transcript: Callable[[str], None] | None = None,
        on_partial: Callable[[str], None] | None = None,
        on_log: Callable[[str], None] | None = None,
        is_muted: Callable[[], bool] | None = None,
        is_speaking: Callable[[], bool] | None = None,
        prefer_local: bool = False,
    ):
        self.on_transcript = on_transcript
        self.on_partial = on_partial
        self.on_log = on_log
        self.is_muted = is_muted or (lambda: False)
        self.is_speaking = is_speaking or (lambda: False)
        self.prefer_local = prefer_local or _has_cloud_session()
        self._active = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client = None
        self._session = None
        self._out_queue: asyncio.Queue | None = None
        self._last_speaking_end = 0.0

    def _log(self, msg: str) -> None:
        if self.on_log:
            try:
                self.on_log(msg)
            except Exception:
                pass

    def _mic_paused(self) -> bool:
        if self.is_muted():
            return True
        if self.is_speaking():
            return True
        if time.monotonic() - self._last_speaking_end < _ECHO_COOLDOWN_SEC:
            return True
        return False

    def _note_speaking_end(self) -> None:
        if not self.is_speaking():
            self._last_speaking_end = time.monotonic()

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._thread_main, daemon=True, name="emo-stt")
        self._thread.start()

    def stop(self) -> None:
        self._active = False
        self.on_transcript = None
        self.on_partial = None
        self.on_log = None
        loop = self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._request_stop)
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3.0)
        self._thread = None

    def shutdown(self) -> None:
        self.stop()

    def _request_stop(self) -> None:
        loop = self._loop
        if not loop:
            return
        for task in asyncio.all_tasks(loop):
            task.cancel()

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        except Exception as e:
            self._log(f"STT: arrêt — {e}")
        finally:
            loop.close()
            self._loop = None

    async def _run(self) -> None:
        use_gemini = bool(_get_api_key()) and not self.prefer_local
        if not use_gemini:
            self._log("STT: mode local (sounddevice + Google fr-FR).")
            await self._fallback_loop()
            return

        try:
            from google import genai  # noqa: F401

            self._client = genai.Client(api_key=_get_api_key())
            await self._gemini_loop()
        except ImportError:
            self._log("STT: google-genai absent — mode local.")
        except _UseLocalSTT:
            self._log("STT: bascule micro local.")
        except Exception as e:
            if _is_quota_error(e):
                self._log("STT: quota Gemini — mode local.")
            else:
                self._log(f"STT: Gemini indisponible — mode local ({type(e).__name__}).")
        if self._active:
            await self._fallback_loop()

    async def _gemini_loop(self) -> None:
        from google.genai import types

        failures = 0
        while self._active and failures <= _MAX_GEMINI_RETRIES:
            try:
                config = types.LiveConnectConfig(
                    response_modalities=[types.Modality.TEXT],
                    input_audio_transcription=types.AudioTranscriptionConfig(),
                    system_instruction=(
                        "Transcris uniquement la parole de l'utilisateur en français. "
                        "Ne réponds pas."
                    ),
                )
                model = _get_live_model()
                self._out_queue = asyncio.Queue(maxsize=200)
                async with self._client.aio.live.connect(model=model, config=config) as session:
                    self._session = session
                    self._log("STT: micro Gemini Live.")
                    recv_task = asyncio.create_task(self._receive_transcripts())
                    send_task = asyncio.create_task(self._send_realtime())
                    mic_task = asyncio.create_task(self._listen_mic())
                    done, pending = await asyncio.wait(
                        [recv_task, send_task, mic_task],
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                    for t in pending:
                        t.cancel()
                    for t in done:
                        exc = t.exception()
                        if exc:
                            raise exc
                self._session = None
                return
            except asyncio.CancelledError:
                break
            except _UseLocalSTT:
                raise
            except Exception as e:
                failures += 1
                if _is_quota_error(e) or failures > _MAX_GEMINI_RETRIES:
                    raise _UseLocalSTT from e
                await asyncio.sleep(2)

    async def _send_realtime(self) -> None:
        while self._active:
            q = self._out_queue
            if q is None:
                await asyncio.sleep(0.05)
                continue
            msg = await q.get()
            session = self._session
            if session is None:
                continue
            try:
                await session.send_realtime_input(media=msg)
            except Exception as e:
                if _is_quota_error(e):
                    raise _UseLocalSTT from e
                await asyncio.sleep(0.2)

    async def _listen_mic(self) -> None:
        try:
            import sounddevice as sd
        except ImportError as e:
            raise _UseLocalSTT from e

        loop = asyncio.get_event_loop()

        def callback(indata, _frames, _time_info, _status):
            if not self._active or self._mic_paused():
                self._note_speaking_end()
                return
            q = self._out_queue
            if q is None:
                return
            payload = {"data": bytes(indata), "mime_type": "audio/pcm"}
            try:
                asyncio.run_coroutine_threadsafe(q.put(payload), loop)
            except Exception:
                pass

        with sd.InputStream(
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=callback,
        ):
            while self._active:
                await asyncio.sleep(0.1)

    async def _receive_transcripts(self) -> None:
        in_buf: list[str] = []
        while self._active:
            session = self._session
            if session is None:
                await asyncio.sleep(0.05)
                continue
            try:
                async for response in session.receive():
                    sc = response.server_content
                    if not sc:
                        continue
                    if sc.input_transcription and sc.input_transcription.text:
                        txt = _clean_transcript(sc.input_transcription.text)
                        if txt:
                            in_buf.append(txt)
                            if self.on_partial:
                                self.on_partial(txt)
                    if sc.turn_complete:
                        full = _clean_transcript(" ".join(in_buf))
                        in_buf = []
                        if full and self.on_transcript:
                            self.on_transcript(full)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if _is_quota_error(e):
                    raise _UseLocalSTT from e
                await asyncio.sleep(0.3)

    async def _fallback_loop(self) -> None:
        loop = asyncio.get_event_loop()
        self._log("STT: écoute… parlez (français).")
        errors = 0
        try:
            import sounddevice as sd
        except ImportError as e:
            self._log(f"STT: sounddevice absent — {e}")
            return

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
            ) as stream:
                while self._active:
                    if self._mic_paused():
                        self._note_speaking_end()
                        await asyncio.sleep(0.1)
                        continue
                    try:
                        pcm = await loop.run_in_executor(
                            None, self._record_utterance_vad, stream
                        )
                    except Exception as e:
                        errors += 1
                        self._log(f"STT: micro — {e}")
                        if errors >= 5:
                            self._log("STT: micro indisponible — vérifiez permissions Windows.")
                            await asyncio.sleep(5)
                            errors = 0
                        await asyncio.sleep(1)
                        continue
                    errors = 0
                    if not pcm:
                        await asyncio.sleep(0.05)
                        continue
                    try:
                        text = await loop.run_in_executor(None, self._recognize_pcm, pcm)
                    except Exception as e:
                        self._log(f"STT: reconnaissance — {e}")
                        await asyncio.sleep(0.5)
                        continue
                    text = _clean_transcript(text or "")
                    if text and self.on_transcript:
                        self._log(f"STT: « {text[:72]} »")
                        self.on_transcript(text)
                    await asyncio.sleep(0.1)
        except Exception as e:
            self._log(f"STT: micro — {e}")

    def _record_utterance_vad(self, stream=None) -> bytes:
        import numpy as np
        import sounddevice as sd

        block = CHUNK_SIZE
        max_blocks = int(_MAX_UTTERANCE_SEC * SEND_SAMPLE_RATE / block)
        silence_blocks_limit = max(1, int(_SILENCE_SEC * SEND_SAMPLE_RATE / block))
        frames: list[bytes] = []
        silent_blocks = 0
        started = False

        def _read_block(active_stream) -> np.ndarray | None:
            data, _overflowed = active_stream.read(block)
            if data is None or len(data) == 0:
                return None
            return np.asarray(data, dtype=np.int16)

        def _process_chunk(chunk: np.ndarray) -> bool:
            nonlocal started, silent_blocks
            if not self._active or self._mic_paused():
                return False
            rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
            if rms >= _ENERGY_THRESHOLD:
                started = True
                silent_blocks = 0
                frames.append(chunk.tobytes())
            elif started:
                frames.append(chunk.tobytes())
                silent_blocks += 1
                if silent_blocks >= silence_blocks_limit:
                    return False
            return True

        if stream is None:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=block,
            ) as local_stream:
                for _ in range(max_blocks):
                    chunk = _read_block(local_stream)
                    if chunk is None:
                        continue
                    if not _process_chunk(chunk):
                        break
        else:
            for _ in range(max_blocks):
                chunk = _read_block(stream)
                if chunk is None:
                    continue
                if not _process_chunk(chunk):
                    break
        if not frames:
            return b""
        return b"".join(frames)

    def _recognize_pcm(self, pcm: bytes) -> str:
        try:
            import speech_recognition as sr
        except ImportError:
            self._log("STT: pip install SpeechRecognition")
            time.sleep(3)
            return ""

        r = sr.Recognizer()
        r.energy_threshold = _ENERGY_THRESHOLD
        r.dynamic_energy_threshold = True
        audio = sr.AudioData(pcm, SEND_SAMPLE_RATE, 2)
        return self._recognize_audio(r, audio)

    def _recognize_audio(self, r, audio) -> str:
        import speech_recognition as sr

        try:
            return r.recognize_google(audio, language="fr-FR")
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            self._log(f"STT: Google Speech — {e}")
        except Exception as e:
            if "UnknownValue" in type(e).__name__:
                return ""
            self._log(f"STT: {e}")
        return ""
