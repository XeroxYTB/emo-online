"""Détection des providers LLM cloud (OpenAI, Claude, DeepSeek, etc.)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Toujours relire backend/.env (override les vars vides du shell Windows)
_ENV = Path(__file__).resolve().parent / ".env"
if _ENV.exists():
    load_dotenv(_ENV, override=True)

PROVIDER_KEYS = {
    "anthropic": ["ANTHROPIC_API_KEY", "EMERGENT_LLM_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "huggingface": ["HF_TOKEN", "HUGGINGFACE_API_KEY"],
}

# Pool vente — même priorité que llm_config.get_api_key (EMO_USE_SALES_LLM_KEYS)
SALES_PROVIDER_KEYS = {
    "anthropic": ["SALES_ANTHROPIC_API_KEY"],
    "openai": ["SALES_OPENAI_API_KEY"],
    "deepseek": ["SALES_DEEPSEEK_API_KEY"],
    "groq": ["SALES_GROQ_API_KEY"],
    "gemini": ["SALES_GEMINI_API_KEY", "SALES_GOOGLE_API_KEY"],
    "openrouter": ["SALES_OPENROUTER_API_KEY"],
    "huggingface": ["SALES_HF_TOKEN", "SALES_HUGGINGFACE_API_KEY"],
}


def _use_sales_keys() -> bool:
    return os.environ.get("EMO_USE_SALES_LLM_KEYS", "true").lower() in ("1", "true", "yes")


def api_key_available(provider: str) -> bool:
    """True si une clé est configurée (SALES_* prioritaire quand EMO_USE_SALES_LLM_KEYS=true)."""
    if _use_sales_keys():
        for env_key in SALES_PROVIDER_KEYS.get(provider, []):
            if os.environ.get(env_key, "").strip():
                return True
    for env_key in PROVIDER_KEYS.get(provider, []):
        if os.environ.get(env_key, "").strip():
            return True
    return False


async def providers_status() -> dict:
    return {name: api_key_available(name) for name in PROVIDER_KEYS}


def configured_providers() -> list[str]:
    return [name for name in PROVIDER_KEYS if api_key_available(name)]
