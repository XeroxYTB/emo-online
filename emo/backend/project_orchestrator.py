"""Orchestration de projets massifs — découpage, modules, phases persistantes."""
from __future__ import annotations

import re
from typing import Any

SCOPE_NORMAL = "normal"
SCOPE_LARGE = "large"
SCOPE_MEGA = "mega"

_MEGA_SIGNALS = re.compile(
    r"\b(launcher|lanceur|market|marketplace|mod\s*market|boutique|store|"
    r"compte|account|auth|login|instance|gestion|dashboard|admin|"
    r"plateforme|platform|saas|full.?stack|micro.?service|"
    r"complet|enti(?:er|ère)|from scratch|tout\s+en\s+un)\b",
    re.I,
)

_LARGE_SIGNALS = re.compile(
    r"\b(client|mod\b|jeu|game|engine|minecraft|fabric|forge|gradle|"
    r"projet|codebase|application|app\b|build|starter)\b",
    re.I,
)

_MODULE_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\b(auth|compte|login|microsoft|oauth|session)\b", re.I), "auth", "Authentification & comptes"),
    (re.compile(r"\b(instance|profil|profile|installation)\b", re.I), "instances", "Gestion d'instances"),
    (re.compile(r"\b(mod|market|marketplace|curseforge|modrinth|catalogue|store)\b", re.I), "mod_market", "Market / catalogue mods"),
    (re.compile(r"\b(news|actualit|feed|rss)\b", re.I), "news", "Fil d'actualités"),
    (re.compile(r"\b(settings|config|préférence|preference)\b", re.I), "settings", "Paramètres utilisateur"),
    (re.compile(r"\b(download|télécharg|cdn|asset)\b", re.I), "downloads", "Téléchargements & assets"),
    (re.compile(r"\b(ui|interface|gui|frontend|electron|qt|wx)\b", re.I), "ui", "Interface utilisateur"),
    (re.compile(r"\b(api|backend|server|database|db)\b", re.I), "backend", "Backend / API / persistance"),
    (re.compile(r"\b(update|mise\s+à\s+jour|patch|version)\b", re.I), "updates", "Mises à jour"),
    (re.compile(r"\b(java|minecraft|forge|fabric|gradle)\b", re.I), "mc_runtime", "Runtime Minecraft (Java, versions, lancement)"),
]


def classify_project_scope(content: str) -> str:
    text = (content or "").strip()
    if len(text) < 10:
        return SCOPE_NORMAL
    mega_hits = len(_MEGA_SIGNALS.findall(text))
    large_hit = bool(_LARGE_SIGNALS.search(text))
    has_complete = bool(re.search(r"\bcomplet|enti(?:er|ère)|full|tout\s+en\s+un\b", text, re.I))
    # Launcher / plateforme + au moins 2 modules = mega
    if mega_hits >= 2 or (mega_hits >= 1 and has_complete):
        return SCOPE_MEGA
    if mega_hits >= 1 and large_hit:
        return SCOPE_MEGA
    if large_hit or mega_hits >= 1:
        return SCOPE_LARGE
    return SCOPE_NORMAL


_CONTINUATION_RE = re.compile(
    r"\b(continue|continu|suite|reprend|reprends|next|phase\s+suivante|vas[- ]?y|go|encore|poursuis)\b",
    re.I,
)


def is_continuation_request(content: str) -> bool:
    return bool(_CONTINUATION_RE.search(content or ""))


def resolve_project_mode(
    content: str,
    existing_plan: dict[str, Any] | None,
) -> tuple[bool, bool, dict[str, Any] | None]:
    """Retourne (large_project, mega_project, plan) en tenant compte d'un plan persisté."""
    if existing_plan:
        scope = existing_plan.get("scope") or SCOPE_MEGA
        is_mega = scope == SCOPE_MEGA
        is_large = True
        if is_continuation_request(content) or len((content or "").strip()) < 80:
            return is_large, is_mega, existing_plan
        new_scope = classify_project_scope(content)
        if new_scope == SCOPE_MEGA:
            return True, True, existing_plan
        return is_large, is_mega, existing_plan
    scope = classify_project_scope(content)
    if scope == SCOPE_MEGA:
        return True, True, None
    if scope == SCOPE_LARGE:
        return True, False, None
    return False, False, None


def is_large_project_request(content: str) -> bool:
    return classify_project_scope(content) != SCOPE_NORMAL


def is_mega_project_request(content: str) -> bool:
    return classify_project_scope(content) == SCOPE_MEGA


def infer_product_modules(content: str) -> list[dict[str, str]]:
    text = content or ""
    found: dict[str, dict[str, str]] = {}
    for pattern, key, label in _MODULE_PATTERNS:
        if pattern.search(text):
            found[key] = {"id": key, "label": label}
    if not found:
        found["core"] = {"id": "core", "label": "Cœur applicatif"}
    return list(found.values())


def _default_phases(modules: list[dict[str, str]]) -> list[dict[str, Any]]:
    phases: list[dict[str, Any]] = [
        {
            "id": 1,
            "name": "Architecture & recherche",
            "status": "active",
            "tasks": [
                "emo_reflect + plan détaillé",
                "web_search templates / projets open-source similaires",
                "PROJECT.md + ARCHITECTURE.md dans le dossier projet",
            ],
        },
        {
            "id": 2,
            "name": "Scaffold & tooling",
            "status": "pending",
            "tasks": ["Structure repo", "deps", "build", "CI minimal"],
        },
        {
            "id": 3,
            "name": "Cœur minimal fonctionnel (MVP)",
            "status": "pending",
            "tasks": ["Feature centrale compilable/lançable", "tests smoke"],
        },
    ]
    phase_id = 4
    for mod in modules:
        if mod["id"] == "core":
            continue
        phases.append({
            "id": phase_id,
            "name": mod["label"],
            "status": "pending",
            "module": mod["id"],
            "tasks": [f"Implémenter {mod['label']}", "tests module", "intégration"],
        })
        phase_id += 1
    phases.append({
        "id": phase_id,
        "name": "Intégration & polish",
        "status": "pending",
        "tasks": ["Brancher modules", "UX", "docs README", "build release"],
    })
    return phases


def build_initial_project_plan(content: str, project_path: str = "") -> dict[str, Any]:
    modules = infer_product_modules(content)
    title = (content or "").strip().split("\n")[0][:120]
    return {
        "title": title,
        "scope": SCOPE_MEGA,
        "project_path": project_path,
        "modules": modules,
        "phases": _default_phases(modules),
        "current_phase_index": 0,
        "files_written": 0,
        "tools_rounds": 0,
    }


def active_phase(plan: dict[str, Any] | None) -> dict[str, Any] | None:
    if not plan:
        return None
    phases = plan.get("phases") or []
    idx = int(plan.get("current_phase_index") or 0)
    if 0 <= idx < len(phases):
        return phases[idx]
    return phases[0] if phases else None


def advance_phase_if_done(plan: dict[str, Any], *, files_this_session: int = 0) -> dict[str, Any]:
    """Avance la phase si assez de travail a été fait (heuristique simple)."""
    plan = dict(plan)
    phases = list(plan.get("phases") or [])
    idx = int(plan.get("current_phase_index") or 0)
    if not phases or idx >= len(phases):
        return plan
    current = dict(phases[idx])
    tools = int(plan.get("tools_rounds") or 0) + 1
    plan["tools_rounds"] = tools
    plan["files_written"] = int(plan.get("files_written") or 0) + files_this_session
    # Phase 1 → avance après reflect + recherche + 2+ fichiers doc
    if idx == 0 and tools >= 4 and plan["files_written"] >= 2:
        current["status"] = "done"
        phases[idx] = current
        if idx + 1 < len(phases):
            nxt = dict(phases[idx + 1])
            nxt["status"] = "active"
            phases[idx + 1] = nxt
            plan["current_phase_index"] = idx + 1
    elif idx > 0 and files_this_session >= 5 and tools % 3 == 0:
        current["status"] = "done"
        phases[idx] = current
        if idx + 1 < len(phases):
            nxt = dict(phases[idx + 1])
            nxt["status"] = "active"
            phases[idx + 1] = nxt
            plan["current_phase_index"] = idx + 1
    plan["phases"] = phases
    return plan


def build_phase_context_prompt(plan: dict[str, Any] | None) -> str:
    if not plan:
        return ""
    phase = active_phase(plan)
    if not phase:
        return ""
    phases = plan.get("phases") or []
    idx = int(plan.get("current_phase_index") or 0)
    tasks = phase.get("tasks") or []
    task_lines = "\n".join(f"  - {t}" for t in tasks[:6])
    modules = ", ".join(m["label"] for m in (plan.get("modules") or [])[:8])
    return f"""
# PLAN PROJET ACTIF (persisté — suis-le)
Titre: {plan.get('title', '')[:100]}
Modules détectés: {modules}
Phase **{idx + 1}/{len(phases)}** — {phase.get('name', '')} [{phase.get('status', '')}]
Tâches phase courante:
{task_lines}

Règle: termine la phase courante avant de sauter à la suivante. `emo_remember` les jalons importants.
Fichiers de pilotage à maintenir: PROJECT.md (roadmap), ARCHITECTURE.md (modules).
"""


MEGA_PROJECT_EXECUTION_PROMPT = """
# MÉGA-PROJET — ORCHESTRATION PRODUIT COMPLET (actif)

Tu construis un **produit logiciel complet** (launcher, plateforme, SaaS, app multi-modules).
Ce n'est PAS faisable en une réponse — tu es un **architecte + lead dev** qui exécute sur plusieurs heures/sessions.

## Intelligence attendue (obligatoire)
1. **Comprends le produit entier** : liste mentalement TOUS les modules (auth, instances, market, UI, backend…).
2. **Ne demande pas** à Hugo de découper — TU proposes l'architecture et le plan.
3. **Premier tour** : `emo_reflect(thought=..., plan=...)` avec plan **numéroté 8–15 phases**.
4. **Ensuite** : `write_file` → `<projet>/PROJECT.md` (vision + roadmap) et `ARCHITECTURE.md` (modules, stack, dossiers).
5. **web_search** projets open-source comparables + docs APIs (Microsoft auth MC, CurseForge/Modrinth API, Electron+Java, etc.).
6. **Stack** : choisis une stack réaliste (ex. Electron/Tauri + backend local ou API, SQLite/Postgres) — justifie en 2 lignes dans ARCHITECTURE.md.

## Rythme d'exécution
- Max **8 fichiers** par tour agent, puis **build/test** (`exec_shell`).
- Chaque module = dossier/package séparé, pas un seul fichier géant.
- Après chaque phase terminée : 1 paragraphe de statut + `emo_remember` (jalon).
- Si interrompu : au prochain message, lis PROJECT.md + list_dir et **reprends** où tu en étais.

## Interdictions
- Répondre par un roman sans tools.
- Dire « c'est trop gros » ou renvoyer Hugo vers des tutos manuels.
- Inventer des APIs — web_search d'abord.
- Tout mettre dans un seul main.py / App.jsx.

Tu as jusqu'à **120 tours** et **~60 min** de session — utilise-les.

## Reprise multi-session
Si PROJECT.md existe déjà dans le dossier projet : **lis-le en premier** (`read_file`), puis `list_dir` et reprends à la phase active du plan — ne recommence pas from scratch.
"""


def plan_summary_for_ui(plan: dict[str, Any] | None) -> str:
    if not plan:
        return ""
    phase = active_phase(plan)
    phases = plan.get("phases") or []
    idx = int(plan.get("current_phase_index") or 0)
    name = phase.get("name", "") if phase else ""
    done = sum(1 for p in phases if p.get("status") == "done")
    return f"Phase {idx + 1}/{len(phases)} — {name} ({done} terminées)"
