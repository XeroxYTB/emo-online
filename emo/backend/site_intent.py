"""Détection des demandes de site web complet (e-commerce, vitrine, landing)."""
from __future__ import annotations

import re
from pathlib import PureWindowsPath

_SITE_RE = re.compile(
    r"\b(site\s+(web|internet|de\s+vente|d['\u2019]achat|e-?commerce|vitrine|complet|clé\s+en\s+main|cle\s+en\s+main)"
    r"|landing\s+page|boutique\s+en\s+ligne|page\s+de\s+vente|storefront|e-?shop"
    r"|marketplace|plateforme\s+(de\s+)?(vente|revente|achat)"
    r"|achat[\s-]revente|revente\s+(entre\s+particuliers|en\s+ligne)?"
    r"|vinted|leboncoin|le\s+bon\s+coin)\b",
    re.I,
)
_BUILD_RE = re.compile(
    r"\b(fais|fais-moi|crée|creer|génère|genere|build|developpe|développe|construis|monte|codes?|code-moi)\b",
    re.I,
)
_FOLDER_NAME_RE = re.compile(
    r"(?:dossier|folder|répertoire|repertoire)\s+(?:nommé|nomme|appelé|appele|de\s+nom)\s+[\"']?([^\s\"',.]+)[\"']?",
    re.I,
)
_PATH_RE = re.compile(
    r'(?:"([^"]+)"|\'([^\']+)\'|((?:[A-Za-z]:\\|~\\|Desktop\\|Bureau\\)[^\s"\']+))',
)


def is_marketplace_request(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(re.search(
        r"\b(vinted|leboncoin|le\s+bon\s+coin|achat[\s-]revente|revente|marketplace|"
        r"annonces?\s+(en\s+ligne|entre\s+particuliers)|c2c|classified)\b",
        t,
        re.I,
    ))


def is_full_site_request(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if is_marketplace_request(t):
        return True
    if _SITE_RE.search(t):
        return True
    if _BUILD_RE.search(t) and re.search(
        r"\b(site|boutique|e-?commerce|vitrine|landing|page\s+web|marketplace|revente)\b", t, re.I
    ):
        return True
    return False


def resolve_site_output_dir(text: str, agent_context: dict | None = None) -> str:
    """Chemin de sortie — extrait du message ou Bureau/site."""
    ctx = agent_context or {}
    folder_m = _FOLDER_NAME_RE.search(text or "")
    if folder_m:
        folder = folder_m.group(1).strip().strip("\"'")
        if folder:
            desktop = (ctx.get("desktop") or "").strip()
            if desktop:
                return str(PureWindowsPath(desktop) / folder)
            return folder
    for m in _PATH_RE.finditer(text or ""):
        raw = next(g for g in m.groups() if g)
        if raw and ("\\" in raw or "/" in raw or raw.lower().startswith("desktop")):
            p = raw.replace("/", "\\")
            if not re.match(r"^[A-Za-z]:\\", p):
                desktop = ctx.get("desktop") or ""
                if desktop and not p.lower().startswith(desktop.lower()):
                    p = str(PureWindowsPath(desktop) / p.replace("Desktop\\", "").replace("Bureau\\", ""))
            return p.rstrip("\\/")
    desktop = (ctx.get("desktop") or "").strip()
    if desktop:
        return str(PureWindowsPath(desktop) / "site")
    return "site"
