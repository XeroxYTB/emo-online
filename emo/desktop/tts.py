"""Synthèse vocale — Gemini Live (Charon) avec repli edge-tts / pyttsx3."""
from __future__ import annotations

import asyncio
import platform
import subprocess
import sys
import tempfile
import threading
import warnings
from pathlib import Path
from typing import Callable, cast

warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"sounddevice")

from emo.desktop.config import load_config
from emo.desktop.gemini_session import _is_quota_error

CHANNELS = 1
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
_AUDIO_SLICE = 2400
_DEFAULT_LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
_MAX_SPEAK_CHARS = 800


def _get_live_model() -> str:
    cfg = load_config()
    return (cfg.get("gemini_live_model") or _DEFAULT_LIVE_MODEL).strip()


def _get_api_key() -> str:
    return (load_config().get("gemini_api_key") or "").strip()


class EmoSpeechEngine:
    """Moteur TTS non-bloquant — thread asyncio + Gemini Live ou repli local."""

    def __init__(
        self,
        on_speaking_start: Callable[[], None] | None = None,
        on_speaking_end: Callable[[], None] | None = None,
        on_log: Callable[[str], None] | None = None,
        prefer_local: bool = False,
    ):
        self.on_speaking_start = on_speaking_start
        self.on_speaking_end = on_speaking_end
        self.on_log = on_log
        self._prefer_local = prefer_local
        self._muted = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session = None
        self._client = None
        self._audio_queue: asyncio.Queue[bytes] | None = None
        self._speak_queue: asyncio.Queue[str] | None = None
        self._turn_done_event: asyncio.Event | None = None
        self._speaking = False
        self._speaking_lock = threading.Lock()
        self._interrupted = False
        self._use_fallback = prefer_local or not _get_api_key()
        self._running = False

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    def set_prefer_local(self, prefer: bool) -> None:
        self._prefer_local = prefer
        if prefer:
            self._use_fallback = True

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if muted:
            self.interrupt()

    @property
    def is_speaking(self) -> bool:
        with self._speaking_lock:
            return self._speaking

    def _set_speaking(self, value: bool) -> None:
        with self._speaking_lock:
            if self._speaking == value:
                return
            self._speaking = value
        if value:
            if self.on_speaking_start:
                self.on_speaking_start()
        elif self.on_speaking_end:
            self.on_speaking_end()

    def start(self) -> None:
        if self._running:
            return
        if self._prefer_local or not _get_api_key():
            self._use_fallback = True
        self._running = True
        self._thread = threading.Thread(target=self._thread_main, daemon=True, name="emo-tts")
        self._thread.start()
        if self._use_fallback:
            self._log("TTS: mode local (pyttsx3 / edge-tts).")

    def stop(self) -> None:
        self._running = False
        self.on_speaking_start = None
        self.on_speaking_end = None
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

    def speak(self, text: str) -> None:
        text = (text or "").strip()[:_MAX_SPEAK_CHARS]
        if not text or self._muted:
            return
        if self._use_fallback or self._prefer_local:
            threading.Thread(
                target=self._fallback_speak_worker,
                args=(text,),
                daemon=True,
                name="emo-tts-fallback",
            ).start()
            return
        loop = self._loop
        if not loop or not self._speak_queue:
            threading.Thread(
                target=self._fallback_speak_worker,
                args=(text,),
                daemon=True,
                name="emo-tts-fallback",
            ).start()
            return
        asyncio.run_coroutine_threadsafe(self._speak_queue.put(text), loop)

    def interrupt(self) -> None:
        self._interrupted = True
        loop = self._loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._drain_audio(), loop)
        self._set_speaking(False)

    def _request_stop(self) -> None:
        if not self._loop:
            return
        for task in asyncio.all_tasks(self._loop):
            task.cancel()

    async def _drain_audio(self) -> None:
        q = self._audio_queue
        drained = 0
        if q:
            while True:
                try:
                    q.get_nowait()
                    drained += 1
                except asyncio.QueueEmpty:
                    break
        if drained:
            self._log(f"SYS: TTS interrompu — {drained} blocs audio ignorés.")
        self._set_speaking(False)
        if self._turn_done_event:
            self._turn_done_event.clear()

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        except Exception as e:
            self._log(f"TTS: erreur thread — {e}")
        finally:
            loop.close()
            self._loop = None

    async def _run(self) -> None:
        if self._prefer_local or self._use_fallback:
            await self._fallback_loop()
            return
        key = _get_api_key()
        if not key:
            self._use_fallback = True
            await self._fallback_loop()
            return
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            self._use_fallback = True
            self._log("TTS: google-genai absent — repli local.")
            await self._fallback_loop()
            return

        self._client = genai.Client(api_key=key)
        backoff = 3
        while self._running:
            if self._prefer_local or self._use_fallback:
                await self._fallback_loop()
                return
            try:
                await self._live_session(types)
                backoff = 3
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log(f"TTS: Gemini Live — {e}")
                if _is_quota_error(e) or "API key not valid" in str(e) or "1007" in str(e):
                    self._use_fallback = True
                    self._prefer_local = True
                    self._log("TTS: repli local (quota Gemini ou clé invalide).")
                    await self._fallback_loop()
                    return
                backoff = min(backoff * 2, 60)
            if self._running:
                await asyncio.sleep(backoff)

    async def _live_session(self, types) -> None:
        from google.genai import types as gtypes

        config = gtypes.LiveConnectConfig(
            response_modalities=[gtypes.Modality.AUDIO],
            system_instruction=(
                "You are Émo, a French voice assistant. "
                "Read the user's text aloud naturally in French. "
                "Do not add commentary."
            ),
            speech_config=gtypes.SpeechConfig(
                voice_config=gtypes.VoiceConfig(
                    prebuilt_voice_config=gtypes.PrebuiltVoiceConfig(voice_name="Charon")
                )
            ),
        )
        model = _get_live_model()
        self._audio_queue = asyncio.Queue()
        self._speak_queue = asyncio.Queue()
        self._turn_done_event = asyncio.Event()

        async with self._client.aio.live.connect(model=model, config=config) as session:
            self._session = session
            self._log("TTS: Gemini Live connecté (Charon).")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._receive_audio())
                tg.create_task(self._play_audio())
                tg.create_task(self._speak_worker())
        self._session = None

    async def _speak_worker(self) -> None:
        while self._running:
            text = await self._speak_queue.get()
            session = self._session
            if not session or self._use_fallback:
                threading.Thread(
                    target=self._fallback_speak_worker,
                    args=(text,),
                    daemon=True,
                    name="emo-tts-fallback",
                ).start()
                continue
            self._interrupted = False
            try:
                from google.genai import types

                await session.send_client_content(
                    turns=cast(types.ContentDict, {"parts": [{"text": text}]}),
                    turn_complete=True,
                )
            except Exception as e:
                self._log(f"TTS: envoi Gemini — {e}")
                if _is_quota_error(e):
                    self._use_fallback = True
                    self._prefer_local = True
                threading.Thread(
                    target=self._fallback_speak_worker,
                    args=(text,),
                    daemon=True,
                    name="emo-tts-fallback",
                ).start()

    async def _receive_audio(self) -> None:
        while self._running:
            session = self._session
            if session is None:
                await asyncio.sleep(0.05)
                continue
            try:
                async for response in session.receive():
                    if response.data and not self._interrupted:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        data = response.data
                        q = self._audio_queue
                        if q is not None:
                            for i in range(0, len(data), _AUDIO_SLICE):
                                q.put_nowait(data[i : i + _AUDIO_SLICE])
                    sc = response.server_content
                    if sc and sc.turn_complete:
                        if self._turn_done_event:
                            self._turn_done_event.set()
                        if self._interrupted:
                            self._interrupted = False
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._log(f"TTS: réception audio — {e}")
                if _is_quota_error(e):
                    self._use_fallback = True
                    self._prefer_local = True
                await asyncio.sleep(0.5)

    async def _play_audio(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            self._use_fallback = True
            self._log("TTS: sounddevice absent — repli local.")
            return

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()
        try:
            while self._running:
                q = self._audio_queue
                if q is None:
                    await asyncio.sleep(0.05)
                    continue
                try:
                    chunk = await asyncio.wait_for(q.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and q.empty()
                    ):
                        self._set_speaking(False)
                        self._turn_done_event.clear()
                    continue
                self._set_speaking(True)
                try:
                    await asyncio.to_thread(stream.write, chunk)
                except (RuntimeError, asyncio.CancelledError):
                    break
        finally:
            self._set_speaking(False)
            stream.stop()
            stream.close()

    async def _fallback_loop(self) -> None:
        while self._running:
            await asyncio.sleep(0.5)

    def _fallback_speak_worker(self, text: str) -> None:
        if self._muted:
            return
        self._set_speaking(True)
        try:
            if platform.system() == "Windows" and self._try_pyttsx3(text):
                self._log("TTS: pyttsx3 (local).")
                return
            if self._try_edge_tts(text):
                self._log("TTS: edge-tts (local).")
                return
            self._log("TTS: échec — installez pyttsx3 ou edge-tts.")
        finally:
            self._set_speaking(False)

    def _try_pyttsx3(self, text: str) -> bool:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            try:
                for voice in engine.getProperty("voices") or []:
                    name = (getattr(voice, "name", "") or "").lower()
                    vid = (getattr(voice, "id", "") or "").lower()
                    if "french" in name or "fr-" in vid or "hortense" in name:
                        engine.setProperty("voice", voice.id)
                        break
                engine.setProperty("rate", 175)
                engine.say(text)
                engine.runAndWait()
            finally:
                try:
                    engine.stop()
                except Exception:
                    pass
            return True
        except Exception as e:
            self._log(f"TTS: pyttsx3 — {e}")
            return False

    def _try_edge_tts(self, text: str) -> bool:
        path: Path | None = None
        try:
            import edge_tts

            async def _save() -> Path:
                communicate = edge_tts.Communicate(text, "fr-FR-DeniseNeural")
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    out = Path(tmp.name)
                await communicate.save(str(out))
                return out

            path = asyncio.run(_save())
            if self._play_mp3(path):
                return True
            self._log("TTS: lecture mp3 impossible.")
            return False
        except Exception as e:
            self._log(f"TTS: edge-tts — {e}")
            return False
        finally:
            if path:
                path.unlink(missing_ok=True)

    def _play_mp3(self, path: Path) -> bool:
        try:
            from playsound import playsound

            playsound(str(path))
            return True
        except ImportError:
            pass
        except Exception as e:
            self._log(f"TTS: playsound — {e}")
        if platform.system() == "Windows":
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"(New-Object -ComObject WMP.MediaPlayer).openPlayer('{path}'); "
                        "Start-Sleep -Seconds 2; "
                        "while ((New-Object -ComObject WMP.MediaPlayer).playState -eq 3) { Start-Sleep -Milliseconds 200 }",
                    ],
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    timeout=120,
                )
                return True
            except Exception as e:
                self._log(f"TTS: WMP — {e}")
        try:
            if sys.platform == "darwin":
                subprocess.run(["afplay", str(path)], check=False, timeout=120)
                return True
            subprocess.run(["ffplay", "-nodisp", "-autoexit", str(path)], check=False, timeout=120)
            return True
        except Exception:
            return False
