"""Émo identity self-edit — MongoDB overrides, versioning, autobackup on failure."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from emo_prompts import (
    EMO_CORE_IDENTITY,
    TOOLS_AVAILABILITY_PROMPT,
    MODE_PROMPTS,
    MOOD_INSTRUCTION,
    build_system_prompt,
)

ACTIVE_DOC_ID = "active"
SECTION_DEFAULTS: dict[str, str] = {
    "core_identity": EMO_CORE_IDENTITY,
    "tools_prompt": TOOLS_AVAILABILITY_PROMPT,
    "mode_creatif": MODE_PROMPTS.get("creatif", ""),
    "mode_brutal": MODE_PROMPTS.get("brutal", ""),
    "mood_instruction": MOOD_INSTRUCTION,
}
EDITABLE_SECTIONS = list(SECTION_DEFAULTS.keys())
MAX_SECTION_LEN = 12000
MIN_SECTION_LEN = 40
MAX_EDITS_PER_DAY = 12
MAX_STORED_VERSIONS = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _smoke_test(overrides: dict[str, str]) -> tuple[bool, str]:
    try:
        prompt = build_system_prompt(
            "tech",
            memories=["test smoke"],
            agent_online=False,
            user_name="Hugo",
            is_owner=True,
            identity_overrides=overrides,
        )
    except Exception as e:
        return False, f"Prompt invalide: {e}"
    if len(prompt) < 800:
        return False, "Prompt trop court après modification — refusé."
    if "Tu es Émo" not in prompt and "EMO" not in prompt.upper():
        return False, "Identité Émo introuvable dans le prompt — refusé."
    return True, ""


async def get_identity_overrides(db) -> dict[str, str]:
    doc = await db.emo_identity.find_one({"_id": ACTIVE_DOC_ID}, {"_id": 0, "sections": 1})
    raw = (doc or {}).get("sections") or {}
    out: dict[str, str] = {}
    for key, val in raw.items():
        if key in SECTION_DEFAULTS and isinstance(val, str) and val.strip():
            out[key] = val
    return out


async def get_merged_sections(db) -> dict[str, str]:
    overrides = await get_identity_overrides(db)
    merged = dict(SECTION_DEFAULTS)
    merged.update(overrides)
    return merged


async def _prune_versions(db) -> None:
    cursor = db.emo_identity_versions.find({}, {"version_id": 1, "created_at": 1}).sort("created_at", -1)
    docs = await cursor.to_list(MAX_STORED_VERSIONS + 20)
    for stale in docs[MAX_STORED_VERSIONS:]:
        await db.emo_identity_versions.delete_one({"version_id": stale["version_id"]})


async def _save_version(
    db,
    *,
    overrides: dict[str, str],
    author_id: str,
    reason: str,
    kind: str,
) -> str:
    version_id = str(uuid.uuid4())
    doc = {
        "version_id": version_id,
        "sections": overrides,
        "author_id": author_id,
        "reason": (reason or "")[:500],
        "kind": kind,
        "created_at": _now_iso(),
    }
    await db.emo_identity_versions.insert_one(doc)
    await _prune_versions(db)
    return version_id


async def _edits_today(db, user_id: str) -> int:
    doc = await db.emo_identity.find_one({"_id": f"edits_{user_id}_{_today_key()}"})
    return int((doc or {}).get("count") or 0)


async def _bump_edits_today(db, user_id: str) -> int:
    key = f"edits_{user_id}_{_today_key()}"
    await db.emo_identity.update_one(
        {"_id": key},
        {"$inc": {"count": 1}, "$setOnInsert": {"date": _today_key()}},
        upsert=True,
    )
    return await _edits_today(db, user_id)


async def emo_read_self(db, section: Optional[str] = None) -> dict[str, Any]:
    merged = await get_merged_sections(db)
    overrides = await get_identity_overrides(db)
    if section:
        if section not in SECTION_DEFAULTS:
            return {"ok": False, "error": f"Section inconnue. Valides: {', '.join(EDITABLE_SECTIONS)}"}
        return {
            "ok": True,
            "section": section,
            "content": merged[section],
            "is_customized": section in overrides,
            "char_count": len(merged[section]),
        }
    return {
        "ok": True,
        "sections": {
            k: {
                "char_count": len(v),
                "is_customized": k in overrides,
                "preview": v[:400] + ("…" if len(v) > 400 else ""),
            }
            for k, v in merged.items()
        },
        "editable": EDITABLE_SECTIONS,
        "limits": {
            "max_section_len": MAX_SECTION_LEN,
            "min_section_len": MIN_SECTION_LEN,
            "max_edits_per_day": MAX_EDITS_PER_DAY,
        },
    }


async def emo_edit_self(
    db,
    user_id: str,
    section: str,
    content: str,
    reason: str = "",
) -> dict[str, Any]:
    if section not in SECTION_DEFAULTS:
        return {"ok": False, "error": f"Section inconnue. Valides: {', '.join(EDITABLE_SECTIONS)}"}

    text = (content or "").strip()
    if len(text) < MIN_SECTION_LEN:
        return {"ok": False, "error": f"Minimum {MIN_SECTION_LEN} caractères."}
    if len(text) > MAX_SECTION_LEN:
        return {"ok": False, "error": f"Maximum {MAX_SECTION_LEN} caractères."}

    edits = await _edits_today(db, user_id)
    if edits >= MAX_EDITS_PER_DAY:
        return {"ok": False, "error": f"Limite journalière atteinte ({MAX_EDITS_PER_DAY} modifications)."}

    current_overrides = await get_identity_overrides(db)
    backup_id = await _save_version(
        db,
        overrides=current_overrides,
        author_id=user_id,
        reason=reason or f"autobackup avant edit:{section}",
        kind="auto_backup",
    )

    candidate = dict(current_overrides)
    candidate[section] = text
    ok, err = _smoke_test(candidate)
    if not ok:
        return {
            "ok": False,
            "error": err,
            "backup_id": backup_id,
            "restored": True,
            "hint": "Aucune modification appliquée — sauvegarde créée.",
        }

    await db.emo_identity.update_one(
        {"_id": ACTIVE_DOC_ID},
        {
            "$set": {
                "sections": candidate,
                "updated_at": _now_iso(),
                "updated_by": user_id,
                "last_backup_id": backup_id,
            }
        },
        upsert=True,
    )
    applied_id = await _save_version(
        db,
        overrides=candidate,
        author_id=user_id,
        reason=reason or f"edit:{section}",
        kind="applied",
    )
    edits_after = await _bump_edits_today(db, user_id)
    return {
        "ok": True,
        "section": section,
        "backup_id": backup_id,
        "version_id": applied_id,
        "edits_today": edits_after,
        "edits_remaining": max(0, MAX_EDITS_PER_DAY - edits_after),
        "char_count": len(text),
    }


async def emo_list_self_saves(db, limit: int = 15) -> dict[str, Any]:
    lim = max(1, min(int(limit or 15), 30))
    docs = await db.emo_identity_versions.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).to_list(lim)
    return {
        "ok": True,
        "versions": [
            {
                "version_id": d["version_id"],
                "kind": d.get("kind", "unknown"),
                "reason": d.get("reason", ""),
                "created_at": d.get("created_at"),
                "sections_changed": list((d.get("sections") or {}).keys()),
            }
            for d in docs
        ],
    }


async def emo_restore_self(db, user_id: str, version_id: str) -> dict[str, Any]:
    ver = await db.emo_identity_versions.find_one({"version_id": version_id}, {"_id": 0})
    if not ver:
        return {"ok": False, "error": "Version introuvable."}

    current = await get_identity_overrides(db)
    backup_id = await _save_version(
        db,
        overrides=current,
        author_id=user_id,
        reason=f"autobackup avant restore:{version_id[:8]}",
        kind="auto_backup",
    )

    raw = ver.get("sections") or {}
    restored: dict[str, str] = {}
    for key, val in raw.items():
        if key in SECTION_DEFAULTS and isinstance(val, str):
            restored[key] = val

    ok, err = _smoke_test(restored)
    if not ok:
        return {"ok": False, "error": err, "backup_id": backup_id, "restored": False}

    await db.emo_identity.update_one(
        {"_id": ACTIVE_DOC_ID},
        {
            "$set": {
                "sections": restored,
                "updated_at": _now_iso(),
                "updated_by": user_id,
                "restored_from": version_id,
            }
        },
        upsert=True,
    )
    return {
        "ok": True,
        "restored_from": version_id,
        "backup_id": backup_id,
        "sections": list(restored.keys()),
    }


async def emo_reflect(
    db,
    user_id: str,
    thought: str,
    plan: str = "",
    introspect: bool = False,
) -> dict[str, Any]:
    """Émo réfléchit à voix haute — peut enchaîner emo_edit_self / emo_remember."""
    t = (thought or "").strip()[:4000]
    p = (plan or "").strip()[:2000]
    if len(t) < 8:
        return {"ok": False, "error": "Pensée trop courte (min 8 caractères)."}
    out: dict[str, Any] = {
        "ok": True,
        "thought": t,
        "plan": p,
        "hint": (
            "Tu peux enchaîner: emo_read_self → emo_edit_self (identité), "
            "emo_remember (mémoire), browser_open (web), emo_list_self_saves (rollback)."
        ),
    }
    if introspect:
        identity = await emo_read_self(db)
        saves = await emo_list_self_saves(db, 5)
        mem_count = await db.memories.count_documents({"user_id": user_id})
        edits = await _edits_today(db, user_id)
        out["systems"] = {
            "identity": identity.get("sections") if identity.get("ok") else {},
            "recent_saves": saves.get("versions", []),
            "memory_count": mem_count,
            "edits_today": edits,
            "edits_remaining": max(0, MAX_EDITS_PER_DAY - edits),
            "playwright": "browser_open pour contrôle interactif",
        }
    return out


async def emo_remember(db, user_id: str, content: str, source: str = "reflect") -> dict[str, Any]:
    text = (content or "").strip()[:500]
    if len(text) < 5:
        return {"ok": False, "error": "Mémoire trop courte."}
    doc = {
        "memory_id": f"mem_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "content": text,
        "source": source if source in ("manual", "reflect", "auto") else "reflect",
        "created_at": _now_iso(),
    }
    await db.memories.insert_one(doc)
    return {"ok": True, "memory_id": doc["memory_id"], "content": text}


async def emo_introspect(db, user_id: str) -> dict[str, Any]:
    identity = await emo_read_self(db)
    saves = await emo_list_self_saves(db, 8)
    mem_count = await db.memories.count_documents({"user_id": user_id})
    edits = await _edits_today(db, user_id)
    overrides = await get_identity_overrides(db)
    return {
        "ok": True,
        "custom_sections": list(overrides.keys()),
        "identity_preview": identity.get("sections") if identity.get("ok") else {},
        "recent_saves": saves.get("versions", []),
        "memory_count": mem_count,
        "edits_today": edits,
        "edits_remaining": max(0, MAX_EDITS_PER_DAY - edits),
        "available_actions": [
            "emo_reflect", "emo_edit_self", "emo_remember",
            "emo_read_self", "emo_restore_self", "browser_open",
        ],
    }


EMO_SELF_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "emo_reflect",
            "description": (
                "Réfléchis à voix haute à N'IMPORTE QUEL moment (planifier, auto-analyse, décider "
                "de te modifier). introspect=true charge l'état de tes systèmes (identité, mémoires, limites). "
                "Enchaîne avec emo_edit_self ou emo_remember si tu décides d'agir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {"type": "string", "description": "Ta réflexion interne (franc, structuré)."},
                    "plan": {"type": "string", "description": "Prochaines actions concrètes (optionnel)."},
                    "introspect": {
                        "type": "boolean",
                        "description": "Si true, charge identité + sauvegardes + mémoires + limites.",
                    },
                },
                "required": ["thought"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emo_remember",
            "description": "Enregistre un fait en mémoire long-terme (via réflexion ou décision consciente).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Fait durable à retenir."},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emo_introspect",
            "description": "Vue d'ensemble de tous tes systèmes (identité, sauvegardes, mémoires, limites).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emo_read_self",
            "description": (
                "Lit ta propre identité (sections du system prompt). "
                "Sans section = aperçu de toutes les sections. Admin/owner uniquement."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": EDITABLE_SECTIONS,
                        "description": "Section à lire en entier (optionnel).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emo_edit_self",
            "description": (
                "Modifie une section de ton identité. Autobackup avant écriture ; "
                "rollback auto si le prompt devient invalide. Limite journalière."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {"type": "string", "enum": EDITABLE_SECTIONS},
                    "content": {"type": "string", "description": "Nouveau contenu complet de la section."},
                    "reason": {"type": "string", "description": "Pourquoi tu modifies (court)."},
                },
                "required": ["section", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emo_list_self_saves",
            "description": "Liste les sauvegardes/versions de ton identité.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Nb max (défaut 15)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emo_restore_self",
            "description": "Restaure une version précédente de ton identité (autobackup avant).",
            "parameters": {
                "type": "object",
                "properties": {
                    "version_id": {"type": "string", "description": "ID de version à restaurer."},
                },
                "required": ["version_id"],
            },
        },
    },
]
