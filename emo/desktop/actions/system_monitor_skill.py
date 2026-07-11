"""Skill monitoring système."""
from __future__ import annotations

from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.system_monitor import SystemMonitor


def run(args: dict) -> Any:
    mon = SystemMonitor()
    stats = mon.snapshot()
    return SkillResult.ok(
        cpu_percent=stats.cpu_percent,
        ram_percent=stats.ram_percent,
        ram_used_mb=stats.ram_used_mb,
        ram_total_mb=stats.ram_total_mb,
        message=stats.summary(),
    )
