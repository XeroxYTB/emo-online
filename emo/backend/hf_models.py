"""Catalogue Hugging Face Inference (router) — modèles gratuits + non censurés par palier."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import ssl_fix  # noqa: F401

import httpx

logger = logging.getLogger("emo.hf_models")

# Non censurés — premium / ultra en priorité
HF_UNCENSORED_MODELS = [
    {"provider": "huggingface", "model": "cognitivecomputations/dolphin-2.9.1-llama-3.1-8b", "label": "Dolphin 3.1 8B (HF — non censuré)"},
    {"provider": "huggingface", "model": "cognitivecomputations/dolphin-2.9.3-mistral-nemo-12b", "label": "Dolphin Mistral 12B (HF — non censuré)"},
    {"provider": "huggingface", "model": "cognitivecomputations/dolphin-2.6-mistral-7b", "label": "Dolphin Mistral 7B (HF — non censuré)"},
    {"provider": "huggingface", "model": "undi95/toppy-m-7b", "label": "Toppy M 7B (HF — non censuré)"},
    {"provider": "huggingface", "model": "davidAU/Llama-3.2-8X3B-MOE-Dark-Champion-Instruct-uncensored-abliterated", "label": "Dark Champion MOE (HF — non censuré)"},
    {"provider": "huggingface", "model": "NoromD/Llama-3.1-8B-Instruct-Uncensored", "label": "Llama 3.1 8B Uncensored (HF)"},
    {"provider": "huggingface", "model": "cognitivecomputations/dolphin-2.9-llama3-8b", "label": "Dolphin Llama3 8B (HF — non censuré)"},
]

# Modèles gratuits courants (petits d'abord = plus fiables au cold start)
HF_STATIC_FREE_MODELS = [
    {"provider": "huggingface", "model": "meta-llama/Meta-Llama-3.1-8B-Instruct", "label": "Llama 3.1 8B (HF — gratuit)"},
    {"provider": "huggingface", "model": "Qwen/Qwen2.5-7B-Instruct", "label": "Qwen 2.5 7B (HF — gratuit)"},
    {"provider": "huggingface", "model": "mistralai/Mistral-7B-Instruct-v0.3", "label": "Mistral 7B (HF — gratuit)"},
    {"provider": "huggingface", "model": "google/gemma-2-9b-it", "label": "Gemma 2 9B (HF — gratuit)"},
    {"provider": "huggingface", "model": "microsoft/Phi-3.5-mini-instruct", "label": "Phi-3.5 Mini (HF — gratuit)"},
    {"provider": "huggingface", "model": "HuggingFaceH4/zephyr-7b-beta", "label": "Zephyr 7B (HF — gratuit)"},
    {"provider": "huggingface", "model": "mistralai/Mistral-Nemo-Instruct-2407", "label": "Mistral Nemo 12B (HF — gratuit)"},
    {"provider": "huggingface", "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B", "label": "DeepSeek R1 Distill 8B (HF — gratuit)"},
    {"provider": "huggingface", "model": "meta-llama/Llama-3.3-70B-Instruct", "label": "Llama 3.3 70B (HF — gratuit)"},
    {"provider": "huggingface", "model": "Qwen/Qwen2.5-72B-Instruct", "label": "Qwen 2.5 72B (HF — gratuit)"},
    {"provider": "huggingface", "model": "moonshotai/Kimi-K2-Instruct-0905", "label": "Kimi K2 (HF — gratuit)"},
    {"provider": "huggingface", "model": "deepseek-ai/DeepSeek-V3-0324", "label": "DeepSeek V3 (HF)"},
    {"provider": "huggingface", "model": "openai/gpt-oss-120b", "label": "GPT-OSS 120B (HF)"},
]

_DYNAMIC_HF: list[dict] = []
_catalog_lock = asyncio.Lock()


def _dedupe(entries: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for entry in entries:
        key = (entry["provider"], entry["model"])
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def hf_models_for_tier(tier: str) -> list[dict]:
    """Liste ordonnée HF pour un palier (non censurés en tête pour premium/ultra)."""
    parts: list[dict] = []
    if tier in ("premium", "ultra"):
        parts.extend(HF_UNCENSORED_MODELS)
    parts.extend(HF_STATIC_FREE_MODELS)
    parts.extend(_DYNAMIC_HF)
    return _dedupe(parts)


def hf_free_models_flat() -> list[dict]:
    """Tous les modèles HF gratuits (tous paliers)."""
    return hf_models_for_tier("ultra")


async def refresh_hf_catalog() -> list[dict]:
    """Synchronise la liste depuis GET /v1/models (flag is_free)."""
    global _DYNAMIC_HF
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.get("https://router.huggingface.co/v1/models")
            resp.raise_for_status()
            rows = resp.json().get("data") or []
        found: list[dict] = []
        static_keys = {(e["provider"], e["model"]) for e in HF_STATIC_FREE_MODELS + HF_UNCENSORED_MODELS}
        for row in rows:
            mid = (row.get("id") or "").strip()
            if not mid or "/" not in mid:
                continue
            providers = row.get("providers") or []
            if not any(p.get("is_free") and p.get("status") == "live" for p in providers):
                continue
            key = ("huggingface", mid)
            if key in static_keys:
                continue
            short = mid.split("/")[-1]
            if len(short) > 36:
                short = short[:33] + "…"
            found.append({
                "provider": "huggingface",
                "model": mid,
                "label": f"{short} (HF — gratuit)",
            })
        async with _catalog_lock:
            _DYNAMIC_HF = found
        logger.info("HF catalog refreshed: %d dynamic free models", len(found))
        return found
    except Exception as exc:
        logger.warning("HF catalog refresh failed: %s", exc)
        return _DYNAMIC_HF


def dynamic_hf_count() -> int:
    return len(_DYNAMIC_HF)
