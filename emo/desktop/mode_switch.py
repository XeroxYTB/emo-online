"""Détection des commandes pour changer de mode (CHAT / VOCAL / AGENT)."""
from __future__ import annotations

import re
import unicodedata

ModeName = str  # "CHAT" | "VOCAL" | "AGENT"

_ALIASES: dict[str, ModeName] = {
    "chat": "CHAT",
    "texte": "CHAT",
    "text": "CHAT",
    "ecrit": "CHAT",
    "écrit": "CHAT",
    "textuel": "CHAT",
    "vocal": "VOCAL",
    "voix": "VOCAL",
    "voice": "VOCAL",
    "micro": "VOCAL",
    "parler": "VOCAL",
    "agent": "AGENT",
    "outils": "AGENT",
    "tools": "AGENT",
    "dev": "AGENT",
}

_SWITCH_VERBS = (
    r"(?:passe|passer|active|activer|activez|met|mets|mettre|switch|basculer|va|aller|ouvre|ouvrir)"
)
_MODE_WORD = r"(?:chat|texte|text|ecrit|textuel|vocal|voix|voice|micro|parler|agent|outils|tools|dev)"
_STOP_VERBS = r"(?:quitte|quitter|arrête|arrete|arrêter|arreter|ferme|fermer|sortir|désactive|desactive|stop|coupe|couper)"


def _normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s'-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _to_mode(word: str) -> ModeName | None:
    return _ALIASES.get(word.strip().lower())


def parse_mode_switch(text: str) -> ModeName | None:
    """Retourne CHAT, VOCAL ou AGENT si le message demande un changement de mode."""
    low = _normalize(text)
    if not low:
        return None

    if re.search(rf"\b{_STOP_VERBS}\s+(?:le|du|au|en)?\s*(?:mode\s+)?(?:vocal|voix|voice|micro|agent|outils)\b", low):
        return "CHAT"

    m = re.search(rf"\bmode\s+({_MODE_WORD})\b", low)
    if m:
        return _to_mode(m.group(1))

    m = re.search(
        rf"\b(?:quel|quelle)\s+(?:est\s+)?(?:le|mon)?\s*mode\b",
        low,
    )
    if m:
        return "STATUS"

    m = re.search(
        rf"\b{_SWITCH_VERBS}\s+(?:en|au|a|sur|vers|dans)?\s*(?:le\s+)?(?:mode\s+)?({_MODE_WORD})\b",
        low,
    )
    if m:
        return _to_mode(m.group(1))

    if re.search(r"\b(?:retour|reviens|revenir)\s+(?:en|au|a|sur)?\s*(?:le\s+)?(?:mode\s+)?(?:chat|texte)\b", low):
        return "CHAT"

    if re.search(r"\b(?:parle|discussion)\s+vocale?\b", low):
        return "VOCAL"

    return None
