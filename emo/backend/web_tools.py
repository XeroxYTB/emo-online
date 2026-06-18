"""Web access tools for Émo — multi-source search (style Cursor) + fetch."""
import ssl_fix  # noqa: F401

import asyncio
import ast
import httpx
import json
import logging
import math
import operator
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger("emo.web")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

FOCUS_SUFFIX = {
    "code": ["site:stackoverflow.com", "site:github.com"],
    "docs": ["documentation", "site:readthedocs.io"],
    "news": ["news"],
}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _dedupe_results(items: list[dict], limit: int) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        url = (item.get("url") or "").split("#")[0].rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)
        item["domain"] = _domain(url)
        out.append(item)
        if len(out) >= limit:
            break
    return out


async def _search_ddg(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    r = await client.get(url)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    results = []
    for el in soup.select("div.result")[: limit + 4]:
        title_a = el.select_one("a.result__a")
        snippet_el = el.select_one(".result__snippet")
        if not title_a:
            continue
        link = title_a.get("href", "")
        m = re.search(r"uddg=([^&]+)", link)
        if m:
            from urllib.parse import unquote
            link = unquote(m.group(1))
        results.append({
            "title": title_a.get_text(strip=True),
            "url": link,
            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            "source": "duckduckgo",
        })
    return results


async def _search_bing(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    r = await client.get(url)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    results = []
    for li in soup.select("li.b_algo")[: limit + 4]:
        a = li.select_one("h2 a")
        if not a:
            continue
        link = a.get("href", "")
        snippet_el = li.select_one(".b_caption p") or li.select_one("p")
        results.append({
            "title": a.get_text(strip=True),
            "url": link,
            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            "source": "bing",
        })
    return results


def _expand_queries(query: str, focus: str) -> list[str]:
    q = query.strip()
    if not q:
        return []
    queries = [q]
    focus = (focus or "general").lower()
    for suffix in FOCUS_SUFFIX.get(focus, []):
        variant = f"{q} {suffix}".strip()
        if variant not in queries:
            queries.append(variant)
    return queries[:3]


async def web_search(
    query: str,
    limit: int = 10,
    focus: str = "general",
    queries: list | None = None,
) -> dict:
    """Multi-source web search with focus modes (Cursor-style research)."""
    search_queries = queries if queries else _expand_queries(query, focus)
    if not search_queries:
        return {"ok": False, "error": "query missing"}
    limit = max(1, min(int(limit or 10), 20))

    try:
        async with httpx.AsyncClient(
            timeout=22,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
            follow_redirects=True,
        ) as client:
            merged: list[dict] = []
            for sq in search_queries:
                ddg, bing = await asyncio.gather(
                    _search_ddg(client, sq, limit),
                    _search_bing(client, sq, limit),
                    return_exceptions=True,
                )
                if isinstance(ddg, list):
                    merged.extend(ddg)
                if isinstance(bing, list):
                    merged.extend(bing)
                if len(_dedupe_results(merged, limit + 5)) >= limit:
                    break

        results = _dedupe_results(merged, limit)
        for i, r in enumerate(results, 1):
            r["rank"] = i

        return {
            "ok": True,
            "query": query,
            "focus": focus,
            "queries_run": search_queries,
            "results": results,
            "count": len(results),
            "hint": "Utilise web_fetch sur les 1-2 URLs les plus pertinentes avant de répondre.",
        }
    except Exception as e:
        logger.exception("web_search failed")
        return {"ok": False, "error": str(e)}


async def web_fetch(url: str, max_chars: int = 12000) -> dict:
    """Fetch a URL and return clean readable text + links + title."""
    if not url or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "URL invalide (doit commencer par http:// ou https://)"}
    try:
        async with httpx.AsyncClient(
            timeout=25,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
        if r.status_code >= 400:
            return {"ok": False, "error": f"HTTP {r.status_code}", "url": url}

        ctype = r.headers.get("content-type", "").lower()
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            text = r.text[:max_chars] if hasattr(r, "text") else ""
            return {
                "ok": True, "url": str(r.url), "title": "",
                "content_type": ctype, "text": text, "links": [], "images": [],
            }

        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        title = (soup.title.get_text(strip=True) if soup.title else "")[:200]
        main = soup.find("main") or soup.find("article") or soup.body or soup
        text = main.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)[:max_chars]

        base = str(r.url)
        links = []
        for a in soup.select("a[href]")[:40]:
            href = a.get("href", "").strip()
            if not href or href.startswith("#"):
                continue
            absolute = urljoin(base, href)
            label = a.get_text(strip=True)[:80]
            if label and absolute.startswith(("http://", "https://")):
                links.append({"text": label, "url": absolute})

        images = []
        for img in soup.select("img[src]")[:20]:
            src = img.get("src", "").strip()
            if src:
                absolute = urljoin(base, src)
                if absolute.startswith(("http://", "https://")):
                    images.append({"url": absolute, "alt": img.get("alt", "")[:80]})

        return {
            "ok": True,
            "url": str(r.url),
            "title": title,
            "content_type": ctype,
            "text": text,
            "links": links[:25],
            "images": images,
            "truncated": len(text) >= max_chars,
        }
    except Exception as e:
        logger.exception("web_fetch failed")
        return {"ok": False, "error": str(e), "url": url}


async def get_datetime(tz_hint: str = "UTC") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "ok": True,
        "iso": now.isoformat(),
        "unix": int(now.timestamp()),
        "timezone": tz_hint or "UTC",
        "weekday": now.strftime("%A"),
    }


async def web_fetch_json(url: str, max_chars: int = 8000) -> dict:
    if not url or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "URL invalide"}
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            r = await client.get(url)
        if r.status_code >= 400:
            return {"ok": False, "error": f"HTTP {r.status_code}", "url": url}
        text = r.text[:max_chars]
        try:
            data = json.loads(text)
            return {"ok": True, "url": str(r.url), "json": data}
        except json.JSONDecodeError:
            return {"ok": True, "url": str(r.url), "text": text, "note": "not valid JSON"}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}


async def github_search(query: str, limit: int = 8) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query missing"}
    return await web_search(q, limit=min(limit, 15), focus="code")


async def stackoverflow_search(query: str, limit: int = 8) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query missing"}
    return await web_search(f"{q} site:stackoverflow.com", limit=min(limit, 15), focus="code")


_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = node.func.id
        args = [_safe_eval(a) for a in node.args]
        if fn == "sqrt" and len(args) == 1:
            return math.sqrt(args[0])
        if fn == "abs" and len(args) == 1:
            return abs(args[0])
        if fn == "round" and 1 <= len(args) <= 2:
            return round(*args)
    raise ValueError("expression non supportée")


def calculate_expression(expression: str) -> dict:
    expr = (expression or "").strip()
    if not expr:
        return {"ok": False, "error": "expression missing"}
    if len(expr) > 200:
        return {"ok": False, "error": "expression trop longue"}
    try:
        tree = ast.parse(expr, mode="eval")
        val = _safe_eval(tree.body)
        return {"ok": True, "expression": expr, "result": val}
    except Exception as e:
        return {"ok": False, "error": str(e), "expression": expr}


WEB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Recherche web multi-sources (DuckDuckGo + Bing), style Cursor. "
                "Retourne title, url, snippet, domain, rank. "
                "focus=code pour Stack Overflow/GitHub, docs pour documentation, news pour actualités. "
                "Enchaîne avec web_fetch sur les meilleurs résultats."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Requête principale."},
                    "limit": {"type": "integer", "description": "Nb max de résultats (défaut 10, max 20)."},
                    "focus": {
                        "type": "string",
                        "enum": ["general", "code", "docs", "news"],
                        "description": "Type de recherche (défaut general).",
                    },
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Variantes de requêtes optionnelles (recherches parallèles).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Récupère le contenu (texte propre + liens + images URLs) d'une page web. Utilise après web_search pour lire doc, README GitHub, Stack Overflow, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL complète (http:// ou https://)."},
                    "max_chars": {"type": "integer", "description": "Limite de caractères du texte extrait (défaut 12000)."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch_json",
            "description": "Récupère une URL JSON (API REST, GitHub raw, etc.) et parse le JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL JSON."},
                    "max_chars": {"type": "integer", "description": "Limite taille réponse."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Date/heure UTC actuelle (pour deadlines, logs, planification).",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "Indication fuseau (info seulement)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_search",
            "description": "Recherche GitHub (repos, issues, code) via web search ciblée.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Requête GitHub."},
                    "limit": {"type": "integer", "description": "Max résultats."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stackoverflow_search",
            "description": "Recherche Stack Overflow pour bugs et solutions code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Question / erreur."},
                    "limit": {"type": "integer", "description": "Max résultats."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculatrice sûre (+ - * / ^ sqrt abs round). Pas de code arbitraire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Ex: (42 * 1.2) + sqrt(16)"},
                },
                "required": ["expression"],
            },
        },
    },
]
