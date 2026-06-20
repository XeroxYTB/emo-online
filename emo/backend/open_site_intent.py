"""Détecte « ouvre ytb / open youtube » et résout l'URL — évite web_search inutile."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if not u.startswith(("http://", "https://")):
        u = f"https://{u}"
    return u

_OPEN = re.compile(
    r"\b(ouvre|ouvres|ouvrez|open|montre|affiche|visite|visit|lance|va\s+sur|go\s+to|"
    r"accède|accede|dirige|mène|mene)\b",
    re.I,
)
_NOISE = re.compile(
    r"\b(le|la|les|un|une|site|web|page|dans le chat|dans le panel|stp|s'il te plait|"
    r"please|moi|mois|pour moi|s'il te plaît)\b",
    re.I,
)

SITE_ALIASES: dict[str, str] = {
    "ytb": "https://www.youtube.com/",
    "youtube": "https://www.youtube.com/",
    "yt": "https://www.youtube.com/",
    "google": "https://www.google.com/",
    "gmail": "https://mail.google.com/",
    "twitter": "https://x.com/",
    "x": "https://x.com/",
    "facebook": "https://www.facebook.com/",
    "fb": "https://www.facebook.com/",
    "instagram": "https://www.instagram.com/",
    "insta": "https://www.instagram.com/",
    "tiktok": "https://www.tiktok.com/",
    "reddit": "https://www.reddit.com/",
    "github": "https://github.com/",
    "discord": "https://discord.com/app",
    "twitch": "https://www.twitch.tv/",
    "netflix": "https://www.netflix.com/",
    "spotify": "https://open.spotify.com/",
    "wikipedia": "https://www.wikipedia.org/",
    "wiki": "https://www.wikipedia.org/",
    "amazon": "https://www.amazon.fr/",
    "chatgpt": "https://chatgpt.com/",
    "hf": "https://huggingface.co/",
    "huggingface": "https://huggingface.co/",
}


def _clean_target(text: str) -> str:
    rest = _OPEN.sub("", text).strip()
    rest = _NOISE.sub("", rest).strip()
    return rest.strip('"\'.,!?;: ')


def resolve_open_site_url(text: str) -> Optional[str]:
    """Retourne l'URL si le message demande d'ouvrir un site connu."""
    raw = (text or "").strip()
    if not raw or not _OPEN.search(raw):
        return None

    target = _clean_target(raw)
    if not target:
        return None

    if re.match(r"https?://", target, re.I):
        return normalize_url(target)
    if re.match(r"www\.", target, re.I):
        return normalize_url(target)

    token = target.lower().split()[0]
    token = re.sub(r"[^a-z0-9.-]", "", token)
    if not token:
        return None

    if token in SITE_ALIASES:
        return SITE_ALIASES[token]

    if "." in token and " " not in target:
        try:
            return normalize_url(token)
        except Exception:
            pass

    for alias, url in SITE_ALIASES.items():
        if token == alias or token.startswith(alias) or alias.startswith(token):
            return url

    return None


def is_simple_open_request(text: str) -> bool:
    """Message court du type « ouvres ytb » sans tâche complexe."""
    if not resolve_open_site_url(text):
        return False
    target = _clean_target(text)
    words = [w for w in target.split() if w]
    if len(words) > 4:
        return False
    complex_hints = re.search(
        r"\b(cherche|recherche|search|code|fichier|crée|créer|mod|bug|fix|imprim|pdf)\b",
        text,
        re.I,
    )
    return not complex_hints


def open_site_label(url: str) -> str:
    try:
        host = urlparse(url).hostname or url
        return host.replace("www.", "")
    except Exception:
        return url
