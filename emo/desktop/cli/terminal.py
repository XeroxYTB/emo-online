"""
Mode terminal Emo Desktop — sans PyQt6, pour tests et debug.

Usage:
    py -3.11 -m emo.desktop --terminal
    py -3.11 -m emo.desktop --terminal --text "bonjour"
    py -3.11 -m emo.desktop --terminal --once --text "bonjour"
    py -3.11 -m emo.desktop --terminal --no-mic

Codes de sortie: 0 succès, 1 erreur (config manquante ou échec chat).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import threading
from typing import Sequence

from emo.desktop.config import load_config
from emo.desktop.core.live_session import EmoLiveSession
from emo.desktop.gemini_session import GeminiSession
from emo.desktop.mode_switch import parse_mode_switch
from emo.desktop.tts import EmoSpeechEngine

_MODE_LABELS = {
    "CHAT": "discussion texte",
    "VOCAL": "vocal — micro actif",
    "AGENT": "agent — planification et outils",
}


def _has_chat_config(cfg: dict) -> bool:
    return bool((cfg.get("gemini_api_key") or "").strip()) or bool(
        (cfg.get("session_token") or "").strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="emo.desktop",
        description="Émo Desktop — interface graphique (défaut) ou mode terminal.",
    )
    p.add_argument(
        "--terminal",
        action="store_true",
        help="Mode terminal sans PyQt6 (logs SYS:/Vous:/Émo: sur stdout).",
    )
    p.add_argument("--text", metavar="MSG", help="Message texte (REPL ou commande unique).")
    p.add_argument(
        "--once",
        action="store_true",
        help="Traiter un seul message puis quitter (avec --text ou première entrée REPL).",
    )
    p.add_argument(
        "--no-mic",
        action="store_true",
        help="Texte seulement — ne démarre pas EmoLiveSession / sounddevice.",
    )
    p.add_argument(
        "--no-tts",
        action="store_true",
        help="Pas de synthèse vocale locale (cloud hybrid).",
    )
    p.add_argument(
        "--test-suite",
        action="store_true",
        help="Suite de tests aléatoires (skills + router) puis quitter.",
    )
    return p


class TerminalApp:
    """Session terminal — chat texte + voix Gemini Live optionnelle."""

    def __init__(self, *, no_mic: bool = False, no_tts: bool = False):
        self.no_mic = no_mic
        self.no_tts = no_tts
        self._mode = "CHAT"
        cfg = load_config()
        self.paired = bool((cfg.get("session_token") or "").strip())
        self._has_gemini_key = bool((cfg.get("gemini_api_key") or "").strip())
        self._chat_lock = threading.Lock()
        self._voice_gen = 0

        self.gemini = GeminiSession(on_log=self._log)
        self._live: EmoLiveSession | None = None
        self._tts: EmoSpeechEngine | None = None

        if not no_mic and self._has_gemini_key:
            self._live = EmoLiveSession(
                on_log=self._log,
                on_user_speech=self._on_voice_transcript,
                on_assistant_speech=self._on_live_assistant,
                cloud_hybrid=self.paired,
            )
            self._live.start()
        elif not no_mic and not self._has_gemini_key:
            self._log("SYS: Pas de gemini_api_key — micro Live désactivé.")

        use_local_tts = not self._has_gemini_key
        if not no_tts and use_local_tts:
            self._tts = EmoSpeechEngine(on_log=self._log, prefer_local=True)
            self._tts.start()

    def _log(self, msg: str) -> None:
        print(msg, flush=True)

    def shutdown(self) -> None:
        if self._live:
            self._live.stop()
        if self._tts:
            self._tts.stop()

    def _on_live_assistant(self, text: str) -> None:
        text = (text or "").strip()
        if not text or (self._live and self._live.cloud_hybrid):
            return
        self._log(f"Émo: {text}")

    def _on_voice_transcript(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self._log(f"Vous: {text}")
        if self._live and not self._live.cloud_hybrid:
            return
        if self._tts:
            self._tts.interrupt()
        if self._live:
            self._live.interrupt()
        with self._chat_lock:
            self._voice_gen += 1
            gen = self._voice_gen

        def _worker():
            reply = asyncio.run(self._handle_message(text, speak=True))
            if gen != self._voice_gen:
                return
            if reply:
                self._log(f"Émo: {reply}")

        threading.Thread(target=_worker, daemon=True, name="emo-term-voice").start()

    async def _handle_message(self, text: str, *, speak: bool = False) -> str:
        target = parse_mode_switch(text)
        if target:
            if target == "STATUS":
                labels = _MODE_LABELS
                return f"Mode actuel : {self._mode} ({labels.get(self._mode, '')})."
            self._mode = target
            return f"Mode {target} — {_MODE_LABELS.get(target, target)}."

        reply = await self.gemini.chat_text(text)
        if speak and reply:
            self._speak_reply(reply)
        return reply

    def _speak_reply(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if self._live and self._live.session:
            self._live.speak(text)
        elif self._tts:
            self._tts.speak(text)

    def process_text(self, text: str, *, speak: bool = True) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        self._log(f"Vous: {text}")
        reply = asyncio.run(self._handle_message(text, speak=speak))
        if reply:
            self._log(f"Émo: {reply}")
        return reply

    def run_repl(self) -> int:
        self._log("SYS: Mode terminal — tapez un message (Ctrl+C pour quitter).")
        if self._live and not self.paired:
            self._log("SYS: Parlez au micro — Gemini Live répond (Charon).")
        elif self._live and self.paired:
            self._log("SYS: Micro Live STT + chat cloud + voix Charon (Live).")
        try:
            while True:
                try:
                    line = input("> ").strip()
                except EOFError:
                    break
                if not line:
                    continue
                if line.lower() in ("quit", "exit", "q"):
                    break
                self.process_text(line)
        except KeyboardInterrupt:
            self._log("SYS: Interruption.")
        finally:
            self.shutdown()
        return 0

    def run_once(self, text: str) -> int:
        try:
            self.process_text(text, speak=not self.no_tts)
            return 0
        finally:
            self.shutdown()


def run_terminal(argv: Sequence[str] | None = None) -> int:
    """Point d'entrée testable — retourne le code de sortie."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.terminal and not getattr(args, "test_suite", False):
        return -1

    if getattr(args, "test_suite", False):
        from emo.desktop.cli.test_suite import run_random_suite

        return run_random_suite(10)

    cfg = load_config()
    if not _has_chat_config(cfg):
        print(
            "ERR: Configurez gemini_api_key ou session_token dans "
            "emo/desktop/config/api_keys.json",
            file=sys.stderr,
        )
        return 1

    app = TerminalApp(no_mic=args.no_mic, no_tts=args.no_tts)

    if args.text:
        return app.run_once(args.text)

    if args.once:
        print("ERR: --once requiert --text.", file=sys.stderr)
        app.shutdown()
        return 1

    return app.run_repl()


def main(argv: Sequence[str] | None = None) -> None:
    code = run_terminal(argv)
    if code >= 0:
        raise SystemExit(code)
