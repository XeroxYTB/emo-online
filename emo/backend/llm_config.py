"""Plans d'abonnement et routage modèles IA cloud."""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from llm_providers import api_key_available

# Modèles cloud reconnus (ChatGPT, Claude, DeepSeek, Gemini…)
# Priorite fallback : Groq gratuit d'abord, puis OpenAI/Gemini, Claude en dernier
# Fallback gratuit : Groq → HF Inference → OpenRouter free → APIs payantes
HF_FREE_MODELS = [
    {"provider": "huggingface", "model": "meta-llama/Llama-3.3-70B-Instruct", "label": "Llama 3.3 70B (HF — gratuit)"},
    {"provider": "huggingface", "model": "moonshotai/Kimi-K2-Instruct-0905", "label": "Kimi K2 (HF — gratuit)"},
]

OPENROUTER_FREE_MODELS = [
    {"provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct:free", "label": "Llama 3.3 70B Free (OpenRouter)"},
    {"provider": "openrouter", "model": "google/gemma-2-9b-it:free", "label": "Gemma 2 9B Free (OpenRouter)"},
    {"provider": "openrouter", "model": "qwen/qwen-2.5-72b-instruct:free", "label": "Qwen 2.5 72B Free (OpenRouter)"},
]

FREE_MODELS = [
    {"provider": "groq", "model": "llama-3.1-8b-instant", "label": "Llama 3.1 8B (Groq — gratuit)"},
    *HF_FREE_MODELS,
    *OPENROUTER_FREE_MODELS,
    {"provider": "groq", "model": "gemma2-9b-it", "label": "Gemma 2 9B (Groq — gratuit)"},
    {"provider": "groq", "model": "mixtral-8x7b-32768", "label": "Mixtral 8x7B (Groq)"},
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (Groq)"},
    {"provider": "openai", "model": "gpt-4o-mini", "label": "ChatGPT 4o mini"},
    {"provider": "gemini", "model": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    {"provider": "gemini", "model": "gemini-2.0-flash-lite", "label": "Gemini 2.0 Flash Lite"},
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku"},
    {"provider": "deepseek", "model": "deepseek-chat", "label": "DeepSeek Chat"},
    {"provider": "openrouter", "model": "openai/gpt-4o-mini", "label": "ChatGPT 4o mini (OpenRouter)"},
    {"provider": "openrouter", "model": "deepseek/deepseek-chat", "label": "DeepSeek Chat (OpenRouter)"},
]

BASIC_MODELS = [
    {"provider": "groq", "model": "llama-3.1-8b-instant", "label": "Llama 3.1 8B (Groq — gratuit)"},
    *HF_FREE_MODELS,
    *OPENROUTER_FREE_MODELS,
    {"provider": "groq", "model": "gemma2-9b-it", "label": "Gemma 2 9B (Groq — gratuit)"},
    {"provider": "groq", "model": "mixtral-8x7b-32768", "label": "Mixtral 8x7B (Groq)"},
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (Groq)"},
    {"provider": "openai", "model": "gpt-4o-mini", "label": "ChatGPT 4o mini"},
    {"provider": "gemini", "model": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    {"provider": "deepseek", "model": "deepseek-chat", "label": "DeepSeek Chat"},
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku"},
    {"provider": "openrouter", "model": "openai/gpt-4o-mini", "label": "ChatGPT 4o mini (OpenRouter)"},
]

PREMIUM_MODELS = [
    {"provider": "groq", "model": "llama-3.1-8b-instant", "label": "Llama 3.1 8B (Groq — gratuit)"},
    *HF_FREE_MODELS,
    {"provider": "groq", "model": "gemma2-9b-it", "label": "Gemma 2 9B (Groq — gratuit)"},
    {"provider": "groq", "model": "mixtral-8x7b-32768", "label": "Mixtral 8x7B (Groq)"},
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (Groq)"},
    {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4"},
    {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet"},
    {"provider": "openai", "model": "gpt-4o-mini", "label": "ChatGPT 4o mini"},
    {"provider": "openai", "model": "gpt-4o", "label": "ChatGPT 4o"},
    {"provider": "deepseek", "model": "deepseek-chat", "label": "DeepSeek Chat"},
    {"provider": "openrouter", "model": "openai/gpt-4o-mini", "label": "ChatGPT 4o mini (OpenRouter)"},
    {"provider": "gemini", "model": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
]

ULTRA_MODELS = [
    {"provider": "groq", "model": "llama-3.1-8b-instant", "label": "Llama 3.1 8B (Groq — gratuit)"},
    *HF_FREE_MODELS,
    *OPENROUTER_FREE_MODELS,
    {"provider": "groq", "model": "gemma2-9b-it", "label": "Gemma 2 9B (Groq — gratuit)"},
    {"provider": "groq", "model": "mixtral-8x7b-32768", "label": "Mixtral 8x7B (Groq)"},
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (Groq)"},
    {"provider": "anthropic", "model": "claude-opus-4-20250514", "label": "Claude Opus 4"},
    {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4"},
    {"provider": "openai", "model": "gpt-4o", "label": "ChatGPT 4o"},
    {"provider": "deepseek", "model": "deepseek-reasoner", "label": "DeepSeek R1 (Reasoner)"},
    {"provider": "deepseek", "model": "deepseek-chat", "label": "DeepSeek Chat"},
    {"provider": "openrouter", "model": "openai/gpt-4o", "label": "ChatGPT 4o (OpenRouter)"},
    {"provider": "gemini", "model": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    {"provider": "gemini", "model": "gemini-2.0-flash-lite", "label": "Gemini 2.0 Flash Lite"},
]

# Modeles retires / invalides (404 API) — jamais proposes
BLOCKED_MODELS = frozenset({
    ("gemini", "gemini-2.5-pro-preview-03-25"),
    ("gemini", "gemini-1.5-flash"),
    ("gemini", "gemini-1.5-pro"),
})

SUBSCRIPTION_PLANS = {
    "free": {
        "id": "free",
        "name": "Gratuit",
        "price_eur": 0,
        "messages_per_day": 15,
        "label": "Essai · 15 msg/jour",
        "models": FREE_MODELS,
        "features": [
            "15 messages par jour",
            "ChatGPT mini · DeepSeek · Gemini",
            "Mémoire + recherche web",
        ],
    },
    "basic": {
        "id": "basic",
        "name": "Basique",
        "price_eur": float(os.environ.get("BASIC_PRICE_EUR", os.environ.get("LICENSE_PRICE_EUR", "15"))),
        "messages_per_day": None,
        "label": "IA cloud · illimité",
        "stripe_link_env": "STRIPE_BASIC_LINK",
        "models": BASIC_MODELS,
        "features": [
            "Messages illimités",
            "ChatGPT · DeepSeek · Gemini · Claude Haiku",
            "Agent local PC",
        ],
    },
    "premium": {
        "id": "premium",
        "name": "Premium",
        "price_eur": 50,
        "messages_per_day": None,
        "label": "Meilleures IA · illimité",
        "stripe_link_env": "STRIPE_PREMIUM_LINK",
        "models": PREMIUM_MODELS,
        "features": [
            "Messages illimités",
            "Claude Sonnet · ChatGPT 4o · DeepSeek",
            "Agent local complet",
        ],
    },
    "ultra": {
        "id": "ultra",
        "name": "Ultra",
        "price_eur": 80,
        "messages_per_day": None,
        "label": "Top du top · illimité",
        "stripe_link_env": "STRIPE_ULTRA_LINK",
        "models": ULTRA_MODELS,
        "features": [
            "Messages illimités",
            "Claude Opus · ChatGPT 4o · DeepSeek R1",
            "Priorité maximale",
        ],
    },
}

TIER_RANK = {"free": 0, "basic": 1, "premium": 2, "ultra": 3}
PAID_TIERS = frozenset({"basic", "premium", "ultra"})

_MISSING_KEYS_HINT = (
    "Aucune clé IA configurée. Ajoute au moins une clé dans backend/.env : "
    "OPENAI_API_KEY (ChatGPT), ANTHROPIC_API_KEY (Claude), DEEPSEEK_API_KEY, "
    "GEMINI_API_KEY ou OPENROUTER_API_KEY (tout-en-un)."
)


def get_user_tier(lic: dict, is_admin: bool = False) -> str:
    if is_admin:
        return "ultra"
    tier = (lic or {}).get("tier")
    if tier in SUBSCRIPTION_PLANS:
        return tier
    if lic.get("paid"):
        return "basic"
    return "free"


def tier_allows_local_agent(tier: str) -> bool:
    return tier in PAID_TIERS


def model_preference_id(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def parse_model_preference(pref: Optional[str]) -> Optional[tuple[str, str]]:
    if not pref or pref.strip().lower() in ("", "auto"):
        return None
    if ":" not in pref:
        return None
    provider, model = pref.split(":", 1)
    provider, model = provider.strip(), model.strip()
    if provider and model:
        return provider, model
    return None


def _provider_ready(provider: str, model: str) -> Optional[tuple[str, str, str]]:
    if (provider, model) in BLOCKED_MODELS:
        return None
    if not api_key_available(provider):
        return None
    try:
        from llm_health import provider_usable
        if not provider_usable(provider, True):
            return None
    except ImportError:
        pass
    return provider, model, model


async def resolve_model_candidates(
    tier: str, preference: Optional[str] = None,
) -> list[tuple[str, str, str]]:
    """Liste ordonnée des modèles disponibles pour un palier (fallback 429/quota)."""
    plan = SUBSCRIPTION_PLANS.get(tier, SUBSCRIPTION_PLANS["free"])
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str, str]] = []
    for entry in plan["models"] + FREE_MODELS + HF_FREE_MODELS + OPENROUTER_FREE_MODELS:
        key = (entry["provider"], entry["model"])
        if key in seen or key in BLOCKED_MODELS:
            continue
        res = _provider_ready(entry["provider"], entry["model"])
        if res:
            seen.add(key)
            p, m, _ = res
            out.append((p, m, entry.get("label", m)))

    pinned = parse_model_preference(preference)
    if not pinned:
        return out

    pp, pm = pinned
    if (pp, pm) in BLOCKED_MODELS:
        return out

    pin_label = pm
    for entry in plan["models"] + FREE_MODELS + HF_FREE_MODELS + OPENROUTER_FREE_MODELS:
        if entry["provider"] == pp and entry["model"] == pm:
            pin_label = entry.get("label", pm)
            break

    rest = [item for item in out if (item[0], item[1]) != (pp, pm)]
    if api_key_available(pp):
        return [(pp, pm, pin_label)] + rest
    return out


async def models_for_tier(tier: str) -> list[dict]:
    """Catalogue UI : auto + modèles disponibles pour le palier."""
    candidates = await resolve_model_candidates(tier)
    items = [{"id": "auto", "label": "Auto (fallback intelligent)", "provider": None, "model": None}]
    seen_ids: set[str] = set()
    for provider, model, label in candidates:
        mid = model_preference_id(provider, model)
        if mid in seen_ids:
            continue
        seen_ids.add(mid)
        items.append({"id": mid, "label": label, "provider": provider, "model": model})
    return items


async def resolve_model(tier: str, preference: Optional[str] = None) -> tuple[str, str, str]:
    candidates = await resolve_model_candidates(tier, preference)
    if not candidates:
        raise ValueError(_MISSING_KEYS_HINT)
    p, m, label = candidates[0]
    return p, m, label


def get_api_key(provider: str, fallback: str = "") -> str:
    mapping = {
        "anthropic": ["ANTHROPIC_API_KEY", "EMERGENT_LLM_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "huggingface": ["HF_TOKEN", "HUGGINGFACE_API_KEY"],
    }
    for key in mapping.get(provider, []):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return (fallback or "").strip()


def plans_for_api() -> list[dict]:
    out = []
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        price = plan["price_eur"]
        if plan_id == "basic":
            price = float(os.environ.get("BASIC_PRICE_EUR", os.environ.get("LICENSE_PRICE_EUR", price)))
        out.append({
            "id": plan_id,
            "name": plan["name"],
            "price_eur": price,
            "label": plan["label"],
            "messages_per_day": plan["messages_per_day"],
            "features": plan["features"],
            "models": [m["label"] for m in plan["models"]],
            "stripe_link": os.environ.get(plan.get("stripe_link_env", ""), "") if plan_id != "free" else None,
        })
    return out


def parse_client_reference(ref: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not ref:
        return None, None
    if "__" in ref:
        uid, tier = ref.split("__", 1)
        return uid, tier if tier in SUBSCRIPTION_PLANS else "basic"
    return ref, "basic"


def stripe_link_for_tier(tier: str) -> str:
    env_map = {"basic": "STRIPE_BASIC_LINK", "premium": "STRIPE_PREMIUM_LINK", "ultra": "STRIPE_ULTRA_LINK"}
    key = env_map.get(tier, "")
    return os.environ.get(key, "") if key else ""
