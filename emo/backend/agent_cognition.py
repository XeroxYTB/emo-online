"""Think + todo — réflexion structurée et plan d'action avant exécution."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

PLANNING_BLOCKED_TOOLS = frozenset({
    "write_file", "edit_file", "exec_shell", "delete_path", "move_path", "apply_patch",
    "download_url", "print_file",
})

_NEW_PROJECT_RE = re.compile(
    r"\b(crée|créer|cree|create|build|fais|fait|code|développe|developpe|projet|app|"
    r"launcher|site|boutique|api|mod\b|jeu|game)\b",
    re.I,
)


def default_cognition(*, planning_required: bool = False) -> dict[str, Any]:
    return {
        "todos": [],
        "thoughts": [],
        "planning_complete": not planning_required,
        "planning_required": planning_required,
    }


def is_new_project_intent(content: str, prior_message_count: int) -> bool:
    if prior_message_count > 3:
        return False
    return bool(_NEW_PROJECT_RE.search(content or ""))


def planning_required_for_session(
    *,
    large_project: bool,
    mega_project: bool,
    content: str,
    prior_message_count: int,
    existing: dict[str, Any] | None,
) -> bool:
    if existing and existing.get("planning_required"):
        return not existing.get("planning_complete", False)
    if large_project or mega_project:
        return True
    if is_new_project_intent(content, prior_message_count):
        return True
    return False


def check_planning_gate(cognition: dict[str, Any], tool_name: str) -> Optional[dict]:
    if not cognition.get("planning_required") or cognition.get("planning_complete"):
        return None
    if tool_name in ("emo_think", "emo_todo", "web_search", "web_fetch", "browser_open",
                     "browser_visit", "browser_snapshot", "get_datetime", "list_dir",
                     "read_file", "grep", "find_files", "codebase_search", "emo_reflect"):
        return None
    if tool_name in PLANNING_BLOCKED_TOOLS:
        return {
            "ok": False,
            "error": (
                "Plan d'action requis avant exécution. "
                "Appelle emo_think (analyse) puis emo_todo(action='set_plan', items=[...]) "
                "avec un plan détaillé, puis emo_todo(action='finalize_plan')."
            ),
            "planning_gate": True,
        }
    return None


def _thought_covers_tool(cognition: dict[str, Any], tool_name: str) -> bool:
    thoughts = cognition.get("thoughts") or []
    if not thoughts:
        return False
    last = thoughts[-1]
    if last.get("before_tool") != tool_name:
        return False
    thought_ts = last.get("ts") or ""
    action_ts = cognition.get("last_action_ts") or ""
    return not action_ts or thought_ts >= action_ts


def mark_action_executed(cognition: dict[str, Any], tool_name: str) -> dict[str, Any]:
    cog = dict(cognition)
    cog["last_action_tool"] = tool_name
    cog["last_action_ts"] = datetime.now(timezone.utc).isoformat()
    return cog


def require_think_before_act(cognition: dict[str, Any], tool_name: str) -> Optional[dict]:
    """Après plan validé : exiger un emo_think récent avant actions lourdes."""
    if tool_name not in PLANNING_BLOCKED_TOOLS:
        return None
    if cognition.get("planning_required") and not cognition.get("planning_complete"):
        return None
    if _thought_covers_tool(cognition, tool_name):
        return None
    thoughts = cognition.get("thoughts") or []
    if not thoughts:
        return {
            "ok": False,
            "error": (
                f"Avant `{tool_name}`, appelle emo_think(thought=..., next_action=..., before_tool='{tool_name}')."
            ),
            "think_gate": True,
        }
    return {
        "ok": False,
        "error": (
            f"Réflexion requise avant `{tool_name}`. "
            f"Appelle emo_think avec before_tool='{tool_name}' (dernière pensée obsolète ou autre outil)."
        ),
        "think_gate": True,
    }


async def load_cognition(db, conversation_id: str, user_id: str) -> dict[str, Any]:
    doc = await db.conversations.find_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"_id": 0, "agent_cognition": 1},
    )
    cog = (doc or {}).get("agent_cognition")
    if isinstance(cog, dict):
        return cog
    return default_cognition()


async def save_cognition(db, conversation_id: str, user_id: str, cognition: dict[str, Any]) -> None:
    await db.conversations.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"$set": {"agent_cognition": cognition}},
    )


async def emo_think(
    db,
    conversation_id: str,
    user_id: str,
    thought: str,
    next_action: str = "",
    before_tool: str = "",
    reasoning: str = "",
) -> dict[str, Any]:
    t = (thought or "").strip()
    if len(t) < 10:
        return {"ok": False, "error": "Pensée trop courte (min 10 caractères)."}
    cog = await load_cognition(db, conversation_id, user_id)
    entry = {
        "id": f"think_{uuid.uuid4().hex[:10]}",
        "thought": t[:4000],
        "reasoning": (reasoning or "").strip()[:2000],
        "next_action": (next_action or "").strip()[:500],
        "before_tool": (before_tool or "").strip()[:64],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    thoughts = list(cog.get("thoughts") or [])
    thoughts.append(entry)
    cog["thoughts"] = thoughts[-40:]
    await save_cognition(db, conversation_id, user_id, cog)
    return {"ok": True, **entry, "hint": "Puis exécute l'action annoncée ou mets à jour emo_todo."}


async def emo_todo(
    db,
    conversation_id: str,
    user_id: str,
    action: str,
    items: list | None = None,
    todo_id: str = "",
    text: str = "",
    status: str = "",
) -> dict[str, Any]:
    act = (action or "list").strip().lower()
    cog = await load_cognition(db, conversation_id, user_id)
    todos: list[dict[str, Any]] = list(cog.get("todos") or [])

    if act == "set_plan":
        raw = items or []
        if not raw:
            return {"ok": False, "error": "items requis pour set_plan (liste de {text, phase?})."}
        todos = []
        for i, it in enumerate(raw[:40]):
            if isinstance(it, str):
                label = it.strip()
                phase = None
            else:
                label = str(it.get("text") or it.get("label") or "").strip()
                phase = it.get("phase")
            if not label:
                continue
            todos.append({
                "id": f"todo_{i + 1}",
                "text": label[:500],
                "status": "pending",
                "phase": phase,
            })
        if len(todos) < 2:
            return {"ok": False, "error": "Plan trop court — minimum 2 tâches détaillées."}
        cog["todos"] = todos
        cog["planning_complete"] = False
        await save_cognition(db, conversation_id, user_id, cog)
        return {"ok": True, "action": act, "todos": todos, "count": len(todos)}

    if act == "add":
        label = (text or "").strip()
        if not label:
            return {"ok": False, "error": "text requis pour add."}
        todos.append({
            "id": f"todo_{uuid.uuid4().hex[:8]}",
            "text": label[:500],
            "status": "pending",
        })
        cog["todos"] = todos
        await save_cognition(db, conversation_id, user_id, cog)
        return {"ok": True, "action": act, "todos": todos}

    if act == "complete":
        tid = (todo_id or "").strip()
        if not tid:
            return {"ok": False, "error": "todo_id requis pour complete."}
        found = False
        for t in todos:
            if t.get("id") == tid:
                t["status"] = "done"
                found = True
                break
        if not found:
            return {"ok": False, "error": f"Todo introuvable: {tid}"}
        cog["todos"] = todos
        await save_cognition(db, conversation_id, user_id, cog)
        return {"ok": True, "action": act, "todos": todos, "completed": tid}

    if act == "update":
        tid = (todo_id or "").strip()
        if not tid:
            return {"ok": False, "error": "todo_id requis pour update."}
        for t in todos:
            if t.get("id") == tid:
                if text:
                    t["text"] = text[:500]
                if status in ("pending", "active", "done"):
                    t["status"] = status
                cog["todos"] = todos
                await save_cognition(db, conversation_id, user_id, cog)
                return {"ok": True, "action": act, "todos": todos}
        return {"ok": False, "error": f"Todo introuvable: {tid}"}

    if act == "finalize_plan":
        if len(todos) < 3:
            return {
                "ok": False,
                "error": "Minimum 3 tâches dans le plan avant finalize_plan. Utilise set_plan d'abord.",
            }
        thoughts = cog.get("thoughts") or []
        if not thoughts:
            return {
                "ok": False,
                "error": "Appelle emo_think avant finalize_plan (analyse + stratégie).",
            }
        cog["planning_complete"] = True
        if todos and todos[0].get("status") == "pending":
            todos[0]["status"] = "active"
        cog["todos"] = todos
        await save_cognition(db, conversation_id, user_id, cog)
        return {
            "ok": True,
            "action": act,
            "todos": todos,
            "planning_complete": True,
            "message": "Plan validé — tu peux exécuter (emo_think avant chaque action lourde).",
        }

    # list (default)
    return {"ok": True, "action": "list", "todos": todos, "planning_complete": cog.get("planning_complete")}


def suggest_plan_items(content: str, *, mega: bool = False) -> list[str]:
    """Skeleton de plan injecté quand planning requis mais pas encore de todos."""
    text = (content or "").lower()
    items: list[str] = [
        "emo_think — analyser demande, stack, risques, architecture cible",
        "web_search — templates / projets open-source similaires",
        "write_file PROJECT.md — vision, scope, stack, structure dossiers",
        "write_file ARCHITECTURE.md — modules, flux, dépendances",
    ]
    if any(k in text for k in ("fastapi", "api", "rest", "plateforme", "saas", "auth", "jwt")):
        items += [
            "Scaffold backend FastAPI + SQLite + modèles User/Project/Task",
            "Routes auth JWT (register/login) + middleware",
            "CRUD projets partagés + todos (statuts, tags, due dates)",
            "Frontend React minimal + docker-compose",
            "Tests pytest + README",
        ]
    elif any(k in text for k in ("cli", "modrinth", "curseforge", "mod", "catalogue")):
        items += [
            "Scaffold pyproject.toml + src/ package",
            "Client API Modrinth + cache SQLite",
            "Commandes CLI (search, list, download, export JSON)",
            "Tests pytest + README",
        ]
    elif any(k in text for k in ("launcher", "electron", "instance", "oauth", "market")):
        items += [
            "Module auth OAuth2 stub",
            "Gestion instances CRUD (JSON persistence)",
            "Catalogue mods API Modrinth",
            "Backend Node/Express + UI Electron minimal",
            "Tests + README + package.json scripts",
        ]
    else:
        items += [
            "Scaffold structure projet + dépendances",
            "Implémenter feature centrale MVP",
            "Tests smoke + README",
        ]
    if mega:
        items.append("Intégration modules + polish + docs release")
    return items[:14 if mega else 10]


def build_cognition_context_prompt(cognition: dict[str, Any] | None, *, content: str = "", mega: bool = False) -> str:
    cog = cognition or {}
    if not cog.get("planning_required") and not cog.get("todos"):
        return ""
    todos = cog.get("todos") or []
    lines = ["\n# COGNITION AGENT — THINK & TODO (actif)"]
    if cog.get("planning_required") and not cog.get("planning_complete"):
        lines.append(
            "**PLAN OBLIGATOIRE** — Avant write_file/exec_shell/edit_file :\n"
            "1. `emo_think` — analyse demande, risques, stack\n"
            "2. `emo_todo(action='set_plan', items=[...])` — plan détaillé (8+ tâches si méga-projet)\n"
            "3. `web_search` si besoin de doc/templates\n"
            "4. `emo_todo(action='finalize_plan')` — valide le plan\n"
            "5. Ensuite seulement : exécution par tâches"
        )
        if not todos and content:
            skeleton = suggest_plan_items(content, mega=mega)
            lines.append("Plan suggéré (copie/adapte dans set_plan) :")
            for i, s in enumerate(skeleton, 1):
                lines.append(f"  {i}. {s}"        )
    elif cog.get("planning_complete"):
        lines.append(
            "Plan validé. **Avant chaque** write_file / exec_shell / edit_file : "
            "`emo_think(thought=..., next_action=..., before_tool='nom_tool')`."
        )
    if todos:
        lines.append("Todo list courante :")
        for t in todos[:15]:
            mark = {"done": "✓", "active": "▸", "pending": "○"}.get(t.get("status"), "○")
            lines.append(f"  {mark} [{t.get('id')}] {t.get('text', '')[:120]}")
    thoughts = cog.get("thoughts") or []
    if thoughts:
        last = thoughts[-1]
        lines.append(f"Dernière réflexion : {last.get('thought', '')[:200]}")
    return "\n".join(lines) + "\n"


AGENT_COGNITION_PROMPT = """
# THINK & TODO — COMME CURSOR / Claude Code

Tu possèdes **emo_think** et **emo_todo** (toujours disponibles en mode Agent).

## Workflow OBLIGATOIRE — début de projet
1. **emo_think** — Comprends la demande, modules, stack, risques. Pas de code yet.
2. **web_search** — Templates, docs, projets similaires open-source.
3. **emo_todo(action='set_plan', items=[...])** — Plan d'action **détaillé** (étapes testables, ordonnées).
4. **emo_todo(action='finalize_plan')** — Valide le plan avant toute écriture de fichier.
5. **write_file** → PROJECT.md + ARCHITECTURE.md reflétant le plan.

## Workflow OBLIGATOIRE — avant chaque action lourde
Avant **write_file**, **edit_file**, **exec_shell**, **delete_path** :
→ **emo_think**(thought="...", next_action="...", before_tool="write_file")
→ Puis l'outil annoncé.
→ **emo_todo(action='complete', todo_id=...)** quand une tâche est finie.

## emo_todo actions
- `set_plan` + items — définir la todo list complète
- `add` + text — ajouter une tâche
- `complete` + todo_id — marquer fait
- `update` + todo_id + status — pending | active | done
- `finalize_plan` — débloquer l'exécution
- `list` — voir la liste

Ne saute jamais la réflexion. Hugo voit tes thinks et todos en direct dans l'UI.
"""


AGENT_COGNITION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "emo_think",
            "description": (
                "Réflexion structurée avant d'agir. OBLIGATOIRE avant write_file/exec_shell/edit_file "
                "et au début de chaque projet. Visible par l'utilisateur en direct."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {"type": "string", "description": "Analyse, raisonnement, décision."},
                    "reasoning": {"type": "string", "description": "Pourquoi cette approche (optionnel)."},
                    "next_action": {"type": "string", "description": "Prochaine action concrète."},
                    "before_tool": {
                        "type": "string",
                        "description": "Nom du tool que tu vas appeler juste après (ex. write_file).",
                    },
                },
                "required": ["thought"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emo_todo",
            "description": (
                "Gère la todo list du projet : plan d'action, suivi des tâches. "
                "set_plan au début, complete après chaque étape, finalize_plan avant d'exécuter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["set_plan", "add", "complete", "update", "finalize_plan", "list"],
                        "description": "Action sur la todo list.",
                    },
                    "items": {
                        "type": "array",
                        "description": "Pour set_plan: [{text, phase?}, ...] ou strings.",
                        "items": {"type": "object"},
                    },
                    "todo_id": {"type": "string", "description": "ID tâche pour complete/update."},
                    "text": {"type": "string", "description": "Texte pour add/update."},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "active", "done"],
                        "description": "Pour update.",
                    },
                },
                "required": ["action"],
            },
        },
    },
]
