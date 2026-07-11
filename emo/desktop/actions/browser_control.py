"""Contrôle navigateur — ouvre URL."""
from __future__ import annotations

import re
import webbrowser
from typing import Any
from urllib.parse import urlparse

from emo.desktop.actions._base import SkillResult


def _extract_url(text: str) -> str | None:
    m = re.search(r"https?://\S+", text)
    if m:
        return m.group(0).rstrip(".,)")
    m = re.search(r"(?:ouvre|open|va sur|visit)\s+(\S+\.\S+)", text, re.I)
    if m:
        host = m.group(1)
        if not host.startswith("http"):
            host = "https://" + host
        return host
    return None


def run(args: dict) -> Any:
    url = args.get("url") or _extract_url(args.get("query") or args.get("prompt") or "")
    if not url:
        return SkillResult.fail("URL requise")
    if not urlparse(url).scheme:
        url = "https://" + url
    webbrowser.open(url)
    return SkillResult.ok(url=url, message=f"Navigateur: {url}")
