"""Surveillance CPU/RAM toutes les 10 secondes."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore


@dataclass
class SystemStats:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0

    def summary(self) -> str:
        return (
            f"CPU {self.cpu_percent:.0f}% | "
            f"RAM {self.ram_percent:.0f}% "
            f"({self.ram_used_mb:.0f}/{self.ram_total_mb:.0f} Mo)"
        )


class SystemMonitor(threading.Thread):
    def __init__(self, interval: float = 10.0, on_update: Callable[[SystemStats], None] | None = None):
        super().__init__(daemon=True, name="emo-system-monitor")
        self.interval = interval
        self.on_update = on_update
        self._stop = threading.Event()
        self.stats = SystemStats()

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> SystemStats:
        if psutil is None:
            return SystemStats()
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            vm = psutil.virtual_memory()
            self.stats = SystemStats(
                cpu_percent=cpu,
                ram_percent=vm.percent,
                ram_used_mb=vm.used / (1024 * 1024),
                ram_total_mb=vm.total / (1024 * 1024),
            )
        except Exception:
            pass
        return self.stats

    def run(self) -> None:
        while not self._stop.is_set():
            stats = self.snapshot()
            if self.on_update:
                try:
                    self.on_update(stats)
                except Exception:
                    pass
            self._stop.wait(self.interval)
