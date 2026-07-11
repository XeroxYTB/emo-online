"""Paramètres système — volume, wifi stub."""
from __future__ import annotations

import subprocess
import sys
from typing import Any

from emo.desktop.actions._base import SkillResult


def run(args: dict) -> Any:
    query = (args.get("query") or "").lower()
    if sys.platform != "win32":
        return SkillResult.fail("computer_settings: Windows uniquement Phase 1")
    if "volume" in query or "son" in query:
        subprocess.Popen("sndvol", shell=True)
        return SkillResult.ok(action="volume_mixer", message="Mixeur de volume ouvert")
    if "wifi" in query or "réseau" in query or "reseau" in query:
        subprocess.Popen("ms-settings:network", shell=True)
        return SkillResult.ok(action="network_settings", message="Paramètres réseau ouverts")
    subprocess.Popen("ms-settings:", shell=True)
    return SkillResult.ok(action="settings", message="Paramètres Windows ouverts")
