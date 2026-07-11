"""Relais long-poll agent — réutilise la logique emo-agent.py en arrière-plan."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import threading
from pathlib import Path
from typing import Callable


def _load_agent_module():
    agent_path = Path(__file__).resolve().parent.parent / "agent" / "emo-agent.py"
    if not agent_path.is_file():
        raise FileNotFoundError(f"emo-agent.py introuvable: {agent_path}")
    spec = importlib.util.spec_from_file_location("emo_agent_relay", agent_path)
    if spec is None or spec.loader is None:
        raise ImportError("Impossible de charger emo-agent.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["emo_agent_relay"] = mod
    spec.loader.exec_module(mod)
    return mod


class AgentRelay(threading.Thread):
    """Thread daemon exécutant la boucle long-poll de l'agent cloud."""

    def __init__(
        self,
        token: str,
        backend_url: str,
        on_status: Callable[[str], None] | None = None,
    ):
        super().__init__(daemon=True, name="emo-agent-relay")
        self.token = token
        self.backend_url = backend_url.rstrip("/")
        self.on_status = on_status
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False
        self._stop = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._running

    def _emit(self, msg: str) -> None:
        if self.on_status:
            try:
                self.on_status(msg)
            except Exception:
                pass

    def run(self) -> None:
        if not self.token:
            self._emit("Relais: token agent manquant")
            return
        try:
            mod = _load_agent_module()
        except Exception as e:
            self._emit(f"Relais: erreur chargement agent — {e}")
            return

        self._running = True
        self._emit(f"Relais: connexion à {self.backend_url}")

        try:
            asyncio.run(mod.run(self.token, self.backend_url))
        except Exception as e:
            self._emit(f"Relais: arrêt — {e}")
        finally:
            self._running = False
            self._emit("Relais: hors ligne")

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        self._running = False
        if self.is_alive():
            self.join(timeout=timeout)


def start_relay_from_env(on_status: Callable[[str], None] | None = None) -> AgentRelay | None:
    """Démarre le relais si EMO_AGENT_TOKEN ou config présente."""
    from emo.desktop.config import backend_base, load_config

    cfg = load_config()
    token = os.environ.get("EMO_AGENT_TOKEN") or cfg.get("agent_token") or ""
    backend = os.environ.get("EMO_BACKEND_URL") or backend_base(cfg.get("backend_url"))
    if not token:
        if on_status:
            on_status("Relais: configurez agent_token dans Paramètres")
        return None
    relay = AgentRelay(token=token, backend_url=backend, on_status=on_status)
    relay.start()
    return relay
