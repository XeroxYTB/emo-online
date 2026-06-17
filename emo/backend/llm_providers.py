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
}


def api_key_available(provider: str) -> bool:
    for env_key in PROVIDER_KEYS.get(provider, []):
        if os.environ.get(env_key, "").strip():
            return True
    return False


async def providers_status() -> dict:
    return {name: api_key_available(name) for name in PROVIDER_KEYS}


def configured_providers() -> list[str]:
    return [name for name in PROVIDER_KEYS if api_key_available(name)]
