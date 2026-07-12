"""
Session audio Mark-XLVIII — Gemini Live + outils (mode non appairé).

cloud_hybrid=True : STT seulement, pas d'outils dans la config Live.
"""
from __future__ import annotations

import asyncio
import base64
import re
import threading
import time
import traceback
from typing import Callable, cast

from emo.desktop.config import load_config
from emo.desktop.core.briefing import send_startup_briefing
from emo.desktop.core.memory_manager import format_memory_for_prompt, load_memory
from emo.desktop.core.proactive_engine import ProactiveEngine
from emo.desktop.core.tool_declarations import get_tool_declarations
from emo.desktop.core.tool_executor import execute_tool

CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
_AUDIO_SLICE = 2400
_DEFAULT_LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


def _clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()


def _get_live_model() -> str:
    return (load_config().get("gemini_live_model") or _DEFAULT_LIVE_MODEL).strip()


def _get_api_key() -> str:
    return (load_config().get("gemini_api_key") or "").strip()


class EmoLiveSession:
    """Gemini Live — micro + outils (Mark-XLVIII JarvisLive)."""

    def __init__(
        self,
        *,
        on_log: Callable[[str], None] | None = None,
        on_user_speech: Callable[[str], None] | None = None,
        on_assistant_speech: Callable[[str], None] | None = None,
        on_state: Callable[[str], None] | None = None,
        is_muted: Callable[[], bool] | None = None,
        cloud_hybrid: bool = False,
        speak_callback: Callable[[str], None] | None = None,
        agent_folder: str = "",
        current_file: Callable[[], str] | None = None,
        phone_audio_queue: asyncio.Queue | None = None,
        on_shutdown: Callable[[], None] | None = None,
        on_close_camera: Callable[[], None] | None = None,
    ):
        self.on_log = on_log
        self.on_user_speech = on_user_speech
        self.on_assistant_speech = on_assistant_speech
        self.on_state = on_state
        self.is_muted = is_muted or (lambda: False)
        self.cloud_hybrid = cloud_hybrid
        self.speak_callback = speak_callback
        self.agent_folder = agent_folder
        self._current_file = current_file or (lambda: "")
        self.phone_audio_queue = phone_audio_queue
        self.on_shutdown = on_shutdown
        self.on_close_camera = on_close_camera

        self.session = None
        self.audio_in_queue: asyncio.Queue | None = None
        self.out_queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._phone_active = False
        self._interrupted = False
        self._turn_done_event: asyncio.Event | None = None
        self._last_user_speech = time.monotonic()
        self._conn_backoff = 3
        self._active = False
        self._thread: threading.Thread | None = None
        self._tts_playback = False

        self._briefing_sent = False
        self._proactive = ProactiveEngine()
        self._vision_hooks: dict = {
            "pending": None,
            "busy": False,
            "cam_active": False,
            "close_pending": False,
            "last_time": 0.0,
        }

    def _log(self, msg: str) -> None:
        if self.on_log:
            try:
                self.on_log(msg)
            except Exception:
                pass

    def _set_state(self, state: str) -> None:
        if self.on_state:
            try:
                self.on_state(state)
            except Exception:
                pass

    def set_speaking(self, value: bool) -> None:
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self._set_state("SPEAKING")
        elif not self.is_muted():
            self._set_state("LISTENING")

    @property
    def is_speaking(self) -> bool:
        with self._speaking_lock:
            return self._is_speaking

    def start(self) -> None:
        if self._active or not _get_api_key():
            if not _get_api_key():
                self._log("Live: configurez gemini_api_key (Mark-XLVIII).")
            return
        self._active = True
        self._thread = threading.Thread(target=self._thread_main, daemon=True, name="emo-live")
        self._thread.start()

    def stop(self) -> None:
        self._active = False
        loop = self._loop
        if loop and loop.is_running():
            for task in asyncio.all_tasks(loop):
                task.cancel()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=4.0)
        self._thread = None

    def set_phone_active(self, active: bool) -> None:
        self._phone_active = bool(active)

    def interrupt(self) -> None:
        self._interrupted = True
        q = self.audio_in_queue
        if q:
            drained = 0
            while True:
                try:
                    q.get_nowait()
                    drained += 1
                except Exception:
                    break
            if drained:
                self._log(f"SYS: Interrompu — {drained} blocs audio ignorés.")
        self.set_speaking(False)
        if self._turn_done_event:
            self._turn_done_event.clear()
        self._set_state("LISTENING")

    def speak_text(self, text: str) -> None:
        """Envoie du texte à la session live (Charon lit à voix haute)."""
        text = (text or "").strip()
        if not text or not self._loop or not self.session:
            return
        self._tts_playback = True
        asyncio.run_coroutine_threadsafe(self._send_text(text), self._loop)

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run())
        except Exception as e:
            self._log(f"Live: arrêt — {e}")
        finally:
            loop.close()
            self._loop = None

    def _build_config(self):
        from google.genai import types
        from datetime import datetime

        sys_prompt = (
            "Tu es Émo, assistant vocal personnel en français. "
            "Réponds naturellement, concis et utile. "
            "Utilise les outils disponibles pour agir — ne simule jamais une action."
        )

        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if not self.cloud_hybrid:
            memory = load_memory() or {}
            mem_str = format_memory_for_prompt(memory)
            if mem_str:
                parts.append(mem_str)
        parts.append(sys_prompt)

        kwargs: dict = {
            "response_modalities": [types.Modality.AUDIO],
            "output_audio_transcription": types.AudioTranscriptionConfig(),
            "input_audio_transcription": types.AudioTranscriptionConfig(),
            "system_instruction": "\n".join(parts),
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
                )
            ),
        }

        if not self.cloud_hybrid:
            kwargs["tools"] = [{"function_declarations": get_tool_declarations()}]

        return types.LiveConnectConfig(**kwargs)

    def _discard_audio_queue(self) -> int:
        q = self.audio_in_queue
        if not q:
            return 0
        drained = 0
        while True:
            try:
                q.get_nowait()
                drained += 1
            except Exception:
                break
        return drained

    async def _send_text(self, text: str) -> None:
        session = self.session
        if not session:
            return
        from google.genai import types

        await session.send_client_content(
            turns=cast(types.ContentDict, {"parts": [{"text": text}]}),
            turn_complete=True,
        )

    async def run(self) -> None:
        import sounddevice as sd  # noqa: F401
        from google import genai

        self._loop = asyncio.get_event_loop()

        while self._active:
            try:
                self._log("Live: connexion Gemini…")
                self._set_state("THINKING")
                config = self._build_config()
                client = genai.Client(
                    api_key=_get_api_key(),
                    http_options={"api_version": "v1beta"},
                )

                async with (
                    client.aio.live.connect(model=_get_live_model(), config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=200)
                    self._turn_done_event = asyncio.Event()
                    self._interrupted = False
                    self._vision_hooks = {
                        "pending": None,
                        "busy": False,
                        "cam_active": False,
                        "close_pending": False,
                        "last_time": 0.0,
                    }

                    self._log("Live: Émo en ligne (Gemini Live — Mark-XLVIII).")
                    self._set_state("LISTENING")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

                    if not self.cloud_hybrid:
                        tg.create_task(self._run_system_monitor())
                        tg.create_task(self._run_proactive_mode())
                        if self.phone_audio_queue is not None:
                            tg.create_task(self._relay_phone_audio())
                        if not self._briefing_sent:
                            self._briefing_sent = True
                            tg.create_task(send_startup_briefing(self))

            except KeyboardInterrupt:
                raise
            except asyncio.CancelledError:
                break
            except BaseException as e:
                err_str = str(e)
                self._log(f"Live: {type(e).__name__} — {e}")
                traceback.print_exc()
                if "API key not valid" in err_str or "1007" in err_str:
                    self._log("ERR: Clé API invalide — vérifiez Paramètres.")
                    self._set_state("SLEEPING")
                    break
                is_net_err = any(
                    k in err_str
                    for k in (
                        "TimeoutError",
                        "timed out",
                        "getaddrinfo",
                        "CancelledError",
                        "ConnectionRefusedError",
                        "OSError",
                        "Cannot connect",
                        "1011",
                        "unavailable",
                    )
                )
                if is_net_err:
                    self._conn_backoff = min(self._conn_backoff * 2, 60)
                    self._log(f"NET: reconnexion dans {self._conn_backoff}s…")
                else:
                    self._conn_backoff = 3
            finally:
                self.session = None

            self.set_speaking(False)
            if not self._active:
                break
            self._set_state("SLEEPING")
            await asyncio.sleep(self._conn_backoff)

    async def _send_realtime(self) -> None:
        while True:
            msg = await self.out_queue.get()
            session = self.session
            if session is None:
                await asyncio.sleep(0.05)
                continue
            await session.send_realtime_input(media=msg)

    async def _listen_audio(self) -> None:
        import sounddevice as sd

        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.is_muted() and not self._phone_active:
                data = indata.tobytes()
                loop.call_soon_threadsafe(
                    self.out_queue.put_nowait,
                    {"data": data, "mime_type": "audio/pcm"},
                )

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            self._log(f"Live: micro — {e}")
            raise

    async def _receive_audio(self) -> None:
        from google.genai import types

        out_buf: list[str] = []
        in_buf: list[str] = []

        while True:
            session = self.session
            if session is None:
                await asyncio.sleep(0.05)
                continue
            async for response in session.receive():
                if response.data:
                    if self._interrupted:
                        pass
                    elif self.cloud_hybrid and not self._tts_playback:
                        pass
                    else:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        _audio_data = response.data
                        for i in range(0, len(_audio_data), _AUDIO_SLICE):
                            q = self.audio_in_queue
                            if q is not None:
                                q.put_nowait(_audio_data[i : i + _AUDIO_SLICE])

                if response.server_content:
                    sc = response.server_content

                    if (
                        sc.output_transcription
                        and sc.output_transcription.text
                        and (not self.cloud_hybrid or self._tts_playback)
                    ):
                        txt = _clean_transcript(sc.output_transcription.text)
                        if txt and txt != (out_buf[-1] if out_buf else ""):
                            out_buf.append(txt)

                    if sc.input_transcription and sc.input_transcription.text:
                        txt = _clean_transcript(sc.input_transcription.text)
                        if txt:
                            in_buf.append(txt)
                            self._last_user_speech = time.monotonic()

                    if sc.turn_complete:
                        was_tts = self._tts_playback
                        if self._turn_done_event:
                            self._turn_done_event.set()

                        if self._interrupted:
                            self._interrupted = False
                            self._tts_playback = False
                            in_buf = []
                            out_buf = []
                            continue

                        full_in = " ".join(in_buf).strip()
                        if full_in:
                            full_in = _clean_transcript(full_in)
                            if full_in:
                                if self.cloud_hybrid:
                                    self._tts_playback = False
                                    self._discard_audio_queue()
                                if self.on_user_speech:
                                    self.on_user_speech(full_in)
                        in_buf = []

                        full_out = " ".join(out_buf).strip()
                        if full_out:
                            full_out = _clean_transcript(full_out)
                            if full_out and self.on_assistant_speech:
                                if not self.cloud_hybrid or was_tts:
                                    self.on_assistant_speech(full_out)
                        out_buf = []

                        pending = self._vision_hooks.get("pending")
                        if pending and session:
                            img_b, mime_t, question, angle = pending
                            self._vision_hooks["pending"] = None
                            b64 = base64.b64encode(img_b).decode("ascii")
                            self._log(f"Vision: {len(img_b):,} bytes ({angle}) → session")
                            await session.send_client_content(
                                turns=cast(types.ContentDict, {
                                    "parts": [
                                        {"inline_data": {"mime_type": mime_t, "data": b64}},
                                        {"text": question},
                                    ]
                                }),
                                turn_complete=True,
                            )
                            if self._vision_hooks.get("cam_active"):
                                self._vision_hooks["cam_active"] = False
                                self._vision_hooks["close_pending"] = True
                            else:
                                self._vision_hooks["busy"] = False
                        elif self._vision_hooks.get("close_pending"):
                            self._vision_hooks["close_pending"] = False
                            self._vision_hooks["busy"] = False
                            if self.on_close_camera:
                                async def _cam_close():
                                    await asyncio.sleep(2.0)
                                    try:
                                        self.on_close_camera()
                                    except Exception:
                                        pass
                                asyncio.create_task(_cam_close())

                if response.tool_call and not self.cloud_hybrid:
                    fn_responses = []
                    for fc in response.tool_call.function_calls:
                        self._log(f"TOOL call: {fc.name}")
                        fr = await execute_tool(
                            fc,
                            on_log=self._log,
                            on_state=self._set_state,
                            speak=self.speak_callback,
                            agent_folder=self.agent_folder,
                            current_file=self._current_file(),
                            vision_hooks=self._vision_hooks,
                            on_shutdown=self.on_shutdown,
                            on_close_camera=self.on_close_camera,
                        )
                        fn_responses.append(fr)
                    await session.send_tool_response(function_responses=fn_responses)

    async def _play_audio(self) -> None:
        import sounddevice as sd

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(self.audio_in_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    q = self.audio_in_queue
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and q is not None
                        and q.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                        if self.cloud_hybrid:
                            self._tts_playback = False
                    continue
                self.set_speaking(True)
                try:
                    await asyncio.to_thread(stream.write, chunk)
                except (RuntimeError, asyncio.CancelledError):
                    break
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def _run_system_monitor(self) -> None:
        from emo.desktop.system_monitor import VoiceAlertMonitor

        monitor = VoiceAlertMonitor()
        while True:
            await asyncio.sleep(10)
            alert = await asyncio.to_thread(monitor.check)
            if alert and self.session:
                try:
                    from google.genai import types

                    await self.session.send_client_content(
                        turns=cast(types.ContentDict, {"parts": [{"text": alert}]}),
                        turn_complete=True,
                    )
                except Exception as e:
                    self._log(f"Monitor: {e}")

    async def _run_proactive_mode(self) -> None:
        from google.genai import types

        while True:
            await asyncio.sleep(60)
            if not self.session:
                continue
            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking:
                continue
            if not self._proactive.should_trigger(self._last_user_speech):
                continue
            self._proactive.mark_triggered()
            try:
                memory = await asyncio.to_thread(load_memory)
                prompt = self._proactive.build_prompt(memory)
                await self.session.send_client_content(
                    turns=cast(types.ContentDict, {"parts": [{"text": prompt}]}),
                    turn_complete=True,
                )
                self._log("SYS: Proactive check-in.")
            except Exception as e:
                self._log(f"Proactive: {e}")

    async def _relay_phone_audio(self) -> None:
        q = self.phone_audio_queue
        if q is None:
            return
        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                self._phone_active = False
                continue
            self._phone_active = True
            with self._speaking_lock:
                speaking = self._is_speaking
            if not speaking and not self.is_muted() and self.out_queue:
                try:
                    self.out_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    pass
