"""Sélection intelligente d'outils — style Cursor/Claude (intent-based, pas liste fixe aveugle)."""
from __future__ import annotations

import re
from typing import Iterable

# Intent patterns (fr + en)
_WEB = re.compile(
    r"\b(web|google|duckduckgo|youtube|ytb|github\.com|http|www\.|\.com|cherche|recherche|"
    r"search|doc|documentation|mods?|actualit|news|site)\b",
    re.I,
)
_BROWSER = re.compile(
    r"\b(ouvre|open|visit|navigue|browser|clique|click|tape|type|connecte|login|"
    r"formulaire|page web|site)\b",
    re.I,
)
_CODE = re.compile(
    r"\b(code|fichier|file|bug|fix|git|npm|pip|python|java|rust|mod|minecraft|"
    r"shell|terminal|exec|compile|build|test|grep|read|write|edit|proj)\b",
    re.I,
)
_REFLECT = re.compile(r"\b(réfléch|reflect|modifie.?toi|identité|personnalité|mémoire)\b", re.I)

# Core sets
WEB_CORE = {
    "web_search", "web_fetch", "browser_visit", "browser_open", "browser_snapshot",
    "browser_click", "browser_type", "browser_scroll", "browser_press", "browser_close",
    "github_search", "stackoverflow_search", "get_datetime", "calculate",
}
LOCAL_CORE = {
    "read_file", "write_file", "edit_file", "list_dir", "grep", "find_files",
    "exec_shell", "codebase_search", "delete_path", "move_path", "append_file",
    "apply_patch", "git_status", "git_diff", "download_url",
}
SELF_CORE = {
    "emo_reflect", "emo_remember", "emo_introspect", "emo_read_self",
    "emo_edit_self", "emo_list_self_saves", "emo_restore_self",
}


def _tool_names(tools: list[dict]) -> set[str]:
    out: set[str] = set()
    for t in tools:
        fn = (t.get("function") or {}).get("name", "")
        if fn:
            out.add(fn)
    return out


def _filter_tools(tools: list[dict], allowed: Iterable[str]) -> list[dict]:
    allow = set(allowed)
    return [t for t in tools if (t.get("function") or {}).get("name", "") in allow]


def select_tools_for_message(
    content: str,
    tools: list[dict],
    *,
    agent_online: bool = False,
    is_owner: bool = False,
    tools_enabled: bool = True,
    provider: str = "",
    max_tools: int = 18,
) -> list[dict]:
    """Choisit les outils pertinents pour le message (Cursor-style dynamic tool set)."""
    if not tools_enabled:
        return []
    available = _tool_names(tools)
    if not available:
        return []

    # Modèles capables (Anthropic/OpenAI/DeepSeek) → tous les outils
    if provider and provider not in ("groq", "gemini", "huggingface"):
        return tools

    text = (content or "").strip()
    picked: set[str] = set()

    # Toujours un minimum web (fonctionne sans agent local)
    picked |= WEB_CORE & available

    if _BROWSER.search(text) or _WEB.search(text):
        picked |= WEB_CORE & available

    if agent_online and (_CODE.search(text) or not _WEB.search(text)):
        picked |= LOCAL_CORE & available

    if is_owner and _REFLECT.search(text):
        picked |= SELF_CORE & available
    elif is_owner and agent_online:
        picked |= {"emo_reflect", "emo_remember"} & available

    # Fallback minimal si rien match
    if not picked:
        picked = (WEB_CORE | (LOCAL_CORE if agent_online else set())) & available

    ordered = _filter_tools(tools, picked)
    # Priorité: browser > web > local > self
    priority = [
        "browser_open", "browser_click", "browser_type", "browser_snapshot",
        "web_search", "web_fetch", "browser_visit",
        "read_file", "edit_file", "write_file", "exec_shell", "grep", "find_files",
        "emo_reflect", "emo_edit_self",
    ]
    order_map = {n: i for i, n in enumerate(priority)}
    ordered.sort(key=lambda t: order_map.get((t.get("function") or {}).get("name", ""), 99))
    return ordered[:max_tools]
