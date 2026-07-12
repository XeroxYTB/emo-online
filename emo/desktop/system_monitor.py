"""Surveillance CPU/RAM — métriques UI + alertes vocales."""
from __future__ import annotations

import ctypes
import platform
import threading
import time
from dataclasses import dataclass
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

_OS = platform.system()

DEFAULT_THRESHOLDS = {
    "cpu": 90.0,
    "ram": 90.0,
    "temp": 85.0,
    "gpu": 95.0,
}

_COOLDOWN = 300
_CPU_STREAK = 3

_nvml_lib: object = None
_nvml_ok: object = None


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


def _nvml_gpu() -> float:
    global _nvml_lib, _nvml_ok
    if _nvml_ok is False:
        return -1.0
    try:
        class _Util(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

        if _nvml_lib is None:
            if _OS == "Windows":
                candidates = ("nvml", r"C:\Windows\System32\nvml.dll")
                _load = ctypes.WinDLL
            else:
                candidates = ("libnvidia-ml.so.1", "libnvidia-ml.so", "libnvidia-ml.dylib")
                _load = ctypes.CDLL
            for name in candidates:
                try:
                    lib = _load(name)
                    lib.nvmlInit_v2()
                    _nvml_lib = lib
                    break
                except Exception:
                    continue

        if _nvml_lib is None:
            _nvml_ok = False
            return -1.0

        dev = ctypes.c_void_p()
        _nvml_lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        u = _Util()
        _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u))
        _nvml_ok = True
        return float(u.gpu)
    except Exception:
        _nvml_ok = False
        return -1.0


def _get_gpu_usage() -> float:
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        return float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
    except Exception:
        pass
    return _nvml_gpu()


def _get_cpu_temp() -> float:
    if psutil is None:
        return -1.0
    try:
        temps = psutil.sensors_temperatures()
        for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz", "cpu-thermal"]:
            if name in temps and temps[name]:
                return temps[name][0].current
        for entries in temps.values():
            if entries:
                return entries[0].current
    except Exception:
        pass
    if _OS == "Windows":
        try:
            import wmi  # type: ignore

            w = wmi.WMI(namespace="root/wmi")
            tz = w.MSAcpi_ThermalZoneTemperature()
            if tz:
                return (tz[0].CurrentTemperature / 10.0) - 273.15
        except Exception:
            pass
    return -1.0


class VoiceAlertMonitor:
    """Alertes vocales quand les métriques dépassent les seuils."""

    def __init__(self, thresholds: dict | None = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._last_alert: dict[str, float] = {}
        self._cpu_streak = 0

    def _can_alert(self, key: str) -> bool:
        return (time.monotonic() - self._last_alert.get(key, 0)) > _COOLDOWN

    def _record(self, key: str) -> None:
        self._last_alert[key] = time.monotonic()

    def check(self) -> str | None:
        if psutil is None:
            return None
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            temp = _get_cpu_temp()
            gpu = _get_gpu_usage()
        except Exception:
            return None

        alerts: list[str] = []

        if cpu >= self.thresholds["cpu"]:
            self._cpu_streak += 1
            if self._cpu_streak >= _CPU_STREAK and self._can_alert("cpu"):
                alerts.append(
                    f"[SYSTEM_ALERT] CPU usage has been critically high ({cpu:.0f}%). "
                    "Warn the user in their language and suggest closing heavy applications."
                )
                self._record("cpu")
                self._cpu_streak = 0
        else:
            self._cpu_streak = 0

        if ram >= self.thresholds["ram"] and self._can_alert("ram"):
            alerts.append(
                f"[SYSTEM_ALERT] RAM is at {ram:.0f}% — nearly exhausted. "
                "Warn the user in their language and suggest freeing memory."
            )
            self._record("ram")

        if temp > 0 and temp >= self.thresholds["temp"] and self._can_alert("temp"):
            alerts.append(
                f"[SYSTEM_ALERT] CPU temperature is {temp:.0f}°C — above the safe limit. "
                "Warn the user in their language."
            )
            self._record("temp")

        if gpu >= 0 and gpu >= self.thresholds["gpu"] and self._can_alert("gpu"):
            alerts.append(
                f"[SYSTEM_ALERT] GPU load is at {gpu:.0f}%. "
                "Briefly inform the user in their language."
            )
            self._record("gpu")

        return " ".join(alerts) if alerts else None


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
