"""Routage des commandes: respond|local|run_skill|dev|code|run_project."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class RouteResult:
    action: str
    skill: str | None = None
    args: dict[str, Any] | None = None
    reason: str = ""


SKILL_KEYWORDS: dict[str, list[str]] = {
    "web_search": ["cherche", "recherche", "search", "google", "trouve sur le web"],
    "weather_report": ["météo", "meteo", "weather", "température", "temperature"],
    "open_app": ["ouvre", "open", "lance", "start", "démarre", "demarre"],
    "file_controller": ["fichier", "dossier", "liste", "list_dir", "ls", "répertoire"],
    "local_analyzer_skill": ["analyse", "analyzer", "analyser", "ast", "grep code"],
    "dev_agent_skill": ["projet", "génère", "genere", "crée un site", "cree un site", "build app"],
    "code_helper": ["code", "python", "bug", "fix", "refactor"],
    "browser_control": ["navigateur", "browser", "site web", "url"],
    "youtube_video": ["youtube", "vidéo", "video", "yt"],
    "reminder": ["rappel", "reminder", "rappelle"],
    "send_message": ["message", "sms", "email", "envoie"],
    "print_document": ["imprime", "print", "impression"],
    "run_python_script": ["exécute script", "execute script", "run script"],
    "computer_control": ["clic", "click", "souris", "clavier", "tape"],
    "desktop_control": ["bureau", "desktop", "fenêtre", "fenetre"],
    "system_monitor_skill": ["cpu", "ram", "système", "systeme", "performance"],
    "computer_settings": ["paramètres", "parametres", "settings", "volume", "wifi"],
    "screen_processor": ["écran", "ecran", "screenshot", "capture"],
    "flight_finder": ["vol", "flight", "avion"],
    "game_updater": ["steam", "epic", "fortnite", "minecraft mod"],
    "proactive": ["suggestion", "proactif", "idée", "idee"],
    "agent_actions": ["agent", "outil", "tool"],
    "fallback_agent": ["aide", "help", "que peux-tu"],
    "file_processor": ["convertir", "pdf", "csv", "traiter fichier"],
}


DEV_PATTERNS = [
    r"\b(projet|project|app|application|site)\b",
    r"\b(génère|genere|crée|cree|build|scaffold)\b",
]
CODE_PATTERNS = [
    r"\b(fix|debug|refactor|patch)\b.*\b(code|python|js|bug)\b",
    r"\b(code|python)\b.*\b(fix|debug|erreur)\b",
]
PROJECT_PATTERNS = [
    r"\b(run|lance|exécute|execute)\b.*\b(projet|project)\b",
]


def _match_any(text: str, patterns: list[str]) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def _best_skill(text: str) -> tuple[str | None, str]:
    low = text.lower()
    best_name, best_score, best_kw = None, 0, ""
    for skill, keywords in SKILL_KEYWORDS.items():
        for kw in keywords:
            if kw in low and len(kw) > best_score:
                best_score = len(kw)
                best_name = skill
                best_kw = kw
    return best_name, best_kw


from emo.desktop.mode_switch import parse_mode_switch


def route_message(text: str, *, agent_online: bool = False) -> RouteResult:
    """Route un message utilisateur vers l'action appropriée."""
    text = (text or "").strip()
    if not text:
        return RouteResult(action="respond", reason="message vide")

    if parse_mode_switch(text):
        return RouteResult(action="respond", reason="changement de mode")

    if _match_any(text, PROJECT_PATTERNS):
        return RouteResult(action="run_project", reason="exécution projet")

    if _match_any(text, DEV_PATTERNS):
        return RouteResult(action="dev", skill="dev_agent_skill", args={"prompt": text}, reason="génération projet")

    if _match_any(text, CODE_PATTERNS):
        return RouteResult(action="code", skill="code_helper", args={"prompt": text}, reason="assistance code")

    skill, kw = _best_skill(text)
    if skill:
        args = {"query": text, "prompt": text}
        if skill == "file_controller":
            args["action"] = "list"
            args["path"] = "."
        return RouteResult(
            action="run_skill",
            skill=skill,
            args=args,
            reason=f"mot-clé « {kw} »",
        )

    if agent_online and any(w in text.lower() for w in ("fichier", "shell", "terminal", "exec")):
        return RouteResult(action="local", reason="outil local agent")

    return RouteResult(action="respond", reason="conversation directe")
