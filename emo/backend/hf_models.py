"""Catalogue Hugging Face Inference (router) — modèles vérifiés + non censurés par palier."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import ssl_fix  # noqa: F401

import httpx

logger = logging.getLogger("emo.hf_models")

# IDs explicitement non censurés (HF router, ≤12B, Ollama-trending uncensored)
UNCENSORED_MODEL_IDS = frozenset({
    "Sao10K/L3-8B-Stheno-v3.2",   # trending uncensored roleplay/creative (HF Ollama filter)
    "Sao10K/L3-8B-Lunaris-v1",    # trending uncensored creative writing (HF Ollama filter)
})

# Non censurés — en tête de liste HF (router.huggingface.co/v1, chat OK, ≤12B)
HF_UNCENSORED_MODELS = [
    # Sao10K Stheno — HF trending uncensored ≤8B ; roleplay, créatif, chat libre
    {"provider": "huggingface", "model": "Sao10K/L3-8B-Stheno-v3.2", "label": "Stheno 8B (HF — non censuré)"},
    # Sao10K Lunaris — HF trending uncensored ≤8B ; écriture créative, fiction
    {"provider": "huggingface", "model": "Sao10K/L3-8B-Lunaris-v1", "label": "Lunaris 8B (HF — non censuré)"},
]

# Modèles HF router vérifiés (chat/completions OK, ≤12B) — polyvalents + code
HF_STATIC_FREE_MODELS = [
    # Qwen 2.5 7B — chat/code polyvalent, fiable au cold start
    {"provider": "huggingface", "model": "Qwen/Qwen2.5-7B-Instruct", "label": "Qwen 2.5 7B (HF — gratuit)"},
    # Qwen 2.5 Coder 7B — code dédié, trending HF coder Ollama
    {"provider": "huggingface", "model": "Qwen/Qwen2.5-Coder-7B-Instruct", "label": "Qwen 2.5 Coder 7B (HF — code)"},
    # Llama 3.1 8B — instruct Meta, chat/code/créatif (ID router correct)
    {"provider": "huggingface", "model": "meta-llama/Llama-3.1-8B-Instruct", "label": "Llama 3.1 8B (HF — gratuit)"},
    # Qwen 3.5 9B — nouvelle génération polyvalente ≤9B
    {"provider": "huggingface", "model": "Qwen/Qwen3.5-9B", "label": "Qwen 3.5 9B (HF — gratuit)"},
    # Qwen 3 8B — chat général récent
    {"provider": "huggingface", "model": "Qwen/Qwen3-8B", "label": "Qwen 3 8B (HF — gratuit)"},
    # Gemma 3 4B — petit modèle rapide Google
    {"provider": "huggingface", "model": "google/gemma-3-4b-it", "label": "Gemma 3 4B (HF — gratuit)"},
    # DeepSeek R1 Distill 8B — raisonnement léger
    {"provider": "huggingface", "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B", "label": "DeepSeek R1 Distill 8B (HF)"},
    # Apertus 8B — instruct multilingue (CH/DE/FR/IT…)
    {"provider": "huggingface", "model": "swiss-ai/Apertus-8B-Instruct-2509", "label": "Apertus 8B (HF — multilingue)"},
]

# Modèles retirés du catalogue HF (404 router / plus chat / IDs invalides)
HF_REMOVED_MODELS = frozenset({
    "cognitivecomputations/dolphin-2.9.1-llama-3.1-8b",
    "cognitivecomputations/dolphin-2.9.3-mistral-nemo-12b",
    "cognitivecomputations/dolphin-2.6-mistral-7b",
    "cognitivecomputations/dolphin-2.9-llama3-8b",
    "undi95/toppy-m-7b",
    "davidAU/Llama-3.2-8X3B-MOE-Dark-Champion-Instruct-uncensored-abliterated",
    "NoromD/Llama-3.1-8B-Instruct-Uncensored",
    "meta-llama/Meta-Llama-3.1-8B-Instruct",  # mauvais ID — utiliser Llama-3.1-8B-Instruct
    "mistralai/Mistral-7B-Instruct-v0.3",
    "mistralai/Mistral-Nemo-Instruct-2407",     # pas un modèle chat sur le router
    "google/gemma-2-9b-it",
    "microsoft/Phi-3.5-mini-instruct",
    "HuggingFaceH4/zephyr-7b-beta",
    "meta-llama/Llama-3.3-70B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "moonshotai/Kimi-K2-Instruct-0905",
    "deepseek-ai/DeepSeek-V3-0324",
    "openai/gpt-oss-120b",
})

_DYNAMIC_HF: list[dict] = []
_catalog_lock = asyncio.Lock()

_UNCENSORED_MARKERS = (
    "uncensored", "dolphin", "abliterated", "dark-champion", "toppy-m",
    "stheno", "lunaris", "venice-edition",
)

_LARGE_MODEL_MARKERS = (
    "70b", "72b", "110b", "120b", "180b", "235b", "405b", "671b", "550b", "424b",
)

_SKIP_MODEL_MARKERS = (
    "embed", "whisper", "guard", "prompt-guard", "rerank", "ocr",
    "flux", "stable-diffusion", "tts", "vision", "vl-", "-vl",
)


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


def _likely_leq12b(model_id: str) -> bool:
    low = model_id.lower()
    return not any(m in low for m in _LARGE_MODEL_MARKERS)


def is_uncensored_model(provider: str, model: str) -> bool:
    """True pour modèles HF/OpenRouter Dolphin, Stheno, Lunaris, Venice, etc."""
    if not provider or not model:
        return False
    if provider == "huggingface" and model in UNCENSORED_MODEL_IDS:
        return True
    if provider not in ("huggingface", "openrouter"):
        return False
    low = model.lower()
    return any(m in low for m in _UNCENSORED_MARKERS)


def hf_models_for_tier(tier: str) -> list[dict]:
    """Liste ordonnée HF — non censurés en tête pour tous les paliers."""
    parts: list[dict] = list(HF_UNCENSORED_MODELS)
    parts.extend(HF_STATIC_FREE_MODELS)
    parts.extend(_DYNAMIC_HF)
    return _dedupe(parts)


def hf_free_models_flat() -> list[dict]:
    """Tous les modèles HF (tous paliers)."""
    return hf_models_for_tier("ultra")


async def refresh_hf_catalog() -> list[dict]:
    """Synchronise depuis GET /v1/models — uniquement chat text ≤12B, hors liste statique."""
    global _DYNAMIC_HF
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.get("https://router.huggingface.co/v1/models")
            resp.raise_for_status()
            rows = resp.json().get("data") or []
        found: list[dict] = []
        static_keys = {
            (e["provider"], e["model"])
            for e in HF_STATIC_FREE_MODELS + HF_UNCENSORED_MODELS
        }
        for row in rows:
            mid = (row.get("id") or "").strip()
            if not mid or "/" not in mid or mid in HF_REMOVED_MODELS:
                continue
            if not _likely_leq12b(mid):
                continue
            low = mid.lower()
            if any(m in low for m in _SKIP_MODEL_MARKERS):
                continue
            arch = row.get("architecture") or {}
            ins = arch.get("input_modalities") or ["text"]
            outs = arch.get("output_modalities") or ["text"]
            if "text" not in ins or "text" not in outs:
                continue
            providers = row.get("providers") or []
            if not any(p.get("status") == "live" for p in providers):
                continue
            key = ("huggingface", mid)
            if key in static_keys:
                continue
            short = mid.split("/")[-1]
            if len(short) > 36:
                short = short[:33] + "…"
            suffix = " — non censuré" if is_uncensored_model("huggingface", mid) else " — gratuit"
            found.append({
                "provider": "huggingface",
                "model": mid,
                "label": f"{short} (HF{suffix})",
            })
        async with _catalog_lock:
            _DYNAMIC_HF = found
        logger.info("HF catalog refreshed: %d dynamic models (≤12B chat)", len(found))
        return found
    except Exception as exc:
        logger.warning("HF catalog refresh failed: %s", exc)
        return _DYNAMIC_HF


def dynamic_hf_count() -> int:
    return len(_DYNAMIC_HF)
