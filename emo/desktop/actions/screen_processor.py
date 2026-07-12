"""Capture écran / webcam — port Mark-XLVIII."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

from emo.desktop.actions._base import SkillResult
from emo.desktop.config import load_config

_IMG_MAX_W = 1280
_IMG_MAX_H = 720
_JPEG_Q = 82

try:
    import cv2
    import numpy as np

    _CV2 = True
except ImportError:
    _CV2 = False
    np = None  # type: ignore

try:
    import mss
    import mss.tools

    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image

    _PIL = True
except ImportError:
    _PIL = False

_OUT = Path(__file__).resolve().parent.parent / "data" / "screenshots"


def _get_os() -> str:
    return str(load_config().get("os_system") or "windows").lower()


def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    if not _PIL:
        return img_bytes, f"image/{source_format.lower()}"
    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return img_bytes, f"image/{source_format.lower()}"


def capture_screen() -> tuple[bytes, str]:
    if not _MSS:
        try:
            import pyautogui

            _OUT.mkdir(parents=True, exist_ok=True)
            dest = _OUT / "screen_fallback.png"
            img = pyautogui.screenshot()
            img.save(dest)
            return _compress(dest.read_bytes(), "PNG")
        except ImportError as e:
            raise RuntimeError("Installez mss ou pyautogui pour les captures") from e

    with mss.mss() as sct:
        monitors = sct.monitors
        target = monitors[1] if len(monitors) > 1 else monitors[0]
        shot = sct.grab(target)
        png = mss.tools.to_png(shot.rgb, shot.size)
    return _compress(png, "PNG")


def _cv2_backend() -> int:
    if not _CV2:
        return 0
    os_name = _get_os()
    if os_name == "windows":
        return cv2.CAP_DSHOW
    if os_name == "mac":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


def _probe_camera(index: int, backend: int, warmup: int = 5) -> bool:
    if not _CV2:
        return False
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return False
    for _ in range(warmup):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return False
    return bool(np.mean(frame) > 8)


def _detect_camera_index() -> int:
    backend = _cv2_backend()
    for idx in range(6):
        if _probe_camera(idx, backend):
            return idx
    return 0


def _get_camera_index() -> int:
    cfg = load_config()
    if "camera_index" in cfg:
        return int(cfg["camera_index"])
    return _detect_camera_index()


def capture_camera() -> tuple[bytes, str]:
    if not _CV2:
        raise RuntimeError("OpenCV (cv2) requis pour la webcam")

    index = _get_camera_index()
    backend = _cv2_backend()
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        raise RuntimeError(f"Camera index {index} could not be opened.")

    for _ in range(10):
        cap.read()
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Camera returned no frame.")

    if _PIL:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q)
        return buf.getvalue(), "image/jpeg"

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_Q])
    return buf.tobytes(), "image/jpeg"


def run(args: dict) -> Any:
    angle = (args.get("angle") or "screen").lower().strip()
    text = (args.get("text") or args.get("prompt") or "").strip()
    try:
        if angle == "camera":
            img_b, mime = capture_camera()
            label = "camera"
        else:
            img_b, mime = capture_screen()
            label = "screen"
        _OUT.mkdir(parents=True, exist_ok=True)
        ext = "jpg" if mime == "image/jpeg" else "png"
        dest = _OUT / f"{label}_capture.{ext}"
        dest.write_bytes(img_b)
        return SkillResult.ok(
            path=str(dest),
            bytes=len(img_b),
            mime=mime,
            message=f"Capture {label}: {len(img_b):,} octets — {text[:60] or 'analyse en cours'}",
        )
    except Exception as e:
        return SkillResult.fail(str(e))
