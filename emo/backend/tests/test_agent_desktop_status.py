"""Tests statut agent / desktop heartbeat."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emo.backend.agent_relay import AgentRegistry


def test_desktop_heartbeat_online():
    reg = AgentRegistry()
    reg.desktop_heartbeat("user-1")
    assert reg.is_desktop_online("user-1")
    assert reg.is_desktop_linked("user-1")


def test_desktop_heartbeat_expires():
    reg = AgentRegistry()
    reg._desktop_heartbeats["user-2"] = time.time() - 120
    assert not reg.is_desktop_online("user-2")
