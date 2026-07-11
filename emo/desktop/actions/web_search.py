"""Recherche web via DuckDuckGo (sans clé API)."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from emo.desktop.actions._base import SkillResult


def _ddg_html(query: str, max_results: int = 5) -> list[dict]:
    if httpx is None:
        return []
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "EmoDesktop/0.1"})
        if r.status_code != 200:
            return []
        results = []
        for m in re.finditer(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            r.text,
        ):
            results.append({"url": m.group(1), "title": m.group(2).strip()})
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def _ddg_library(query: str, max_results: int = 5) -> list[dict]:
    try:
        from duckduckgo_search import DDGS  # type: ignore
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []


def run(args: dict) -> Any:
    query = (args.get("query") or args.get("prompt") or "").strip()
    if not query:
        return SkillResult.fail("Requête de recherche requise")
    # Nettoyer préfixe conversationnel
    for prefix in ("cherche ", "recherche ", "search ", "trouve "):
        if query.lower().startswith(prefix):
            query = query[len(prefix):].strip()
            break

    results = _ddg_library(query) or _ddg_html(query)
    if not results:
        return SkillResult.fail("Aucun résultat — vérifiez la connexion")

    lines = [f"• {r.get('title', r.get('body', ''))[:80]}" for r in results[:5]]
    summary = "\n".join(lines)
    return SkillResult.ok(query=query, results=results, summary=summary, message=summary)
