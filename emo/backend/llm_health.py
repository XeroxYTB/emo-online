"""Runtime health probes for LLM providers (quota / auth / connectivity)."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import httpx

from llm_config import get_api_key

logger = logging.getLogger("emo.llm_health")

_PROBE_TTL_SEC = 600
_probe_cache: dict[str, tuple[bool, float, str]] = {}
_probe_lock = asyncio.Lock()

_PROBE_MODELS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.1-8b-instant"),
    "openai": ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    "gemini": ("gemini-2.0-flash-lite", None),
    "anthropic": ("claude-3-5-haiku-20241022", None),
    "deepseek": ("https://api.deepseek.com/chat/completions", "deepseek-chat"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "meta-llama/llama-3.2-3b-instruct:free"),
    "huggingface": ("https://router.huggingface.co/v1/chat/completions", "Qwen/Qwen2.5-7B-Instruct"),
}


def _cache_get(provider: str) -> Optional[tuple[bool, str]]:
    row = _probe_cache.get(provider)
    if not row:
        return None
    ok, ts, msg = row
    if time.monotonic() - ts > _PROBE_TTL_SEC:
        return None
    return ok, msg


def _cache_set(provider: str, ok: bool, msg: str = "") -> None:
    _probe_cache[provider] = (ok, time.monotonic(), msg)


_TRANSIENT_FAILURE = (
    "429", "rate limit", "tpm", "tokens per minute", "too many requests",
    "503", "overloaded", "timeout", "temporarily unavailable",
)


def mark_provider_failed(provider: str, reason: str = "") -> None:
    if provider == "huggingface":
        return
    lower = (reason or "").lower()
    if any(m in lower for m in _TRANSIENT_FAILURE):
        return
    _cache_set(provider, False, reason[:200])


def mark_provider_ok(provider: str) -> None:
    _cache_set(provider, True, "ok")


def provider_usable(provider: str, key_configured: bool) -> bool:
    if not key_configured:
        return False
    cached = _cache_get(provider)
    if cached is None:
        return True
    return cached[0]


async def _probe_openai_compat(provider: str, url: str, model: str, key: str) -> tuple[bool, str]:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply OK"}],
        "max_tokens": 8,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.is_success:
                return True, "ok"
            text = (resp.text or "")[:300]
            return False, f"{resp.status_code}: {text}"
    except Exception as e:
        return False, str(e)[:200]


async def _probe_gemini(model: str, key: str) -> tuple[bool, str]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={key}"
    )
    body = {"contents": [{"role": "user", "parts": [{"text": "Reply OK"}]}], "generationConfig": {"maxOutputTokens": 8}}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=body)
            if resp.is_success:
                return True, "ok"
            return False, f"{resp.status_code}: {(resp.text or '')[:300]}"
    except Exception as e:
        return False, str(e)[:200]


async def _probe_anthropic(model: str, key: str) -> tuple[bool, str]:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return False, "anthropic package missing"
    try:
        client = AsyncAnthropic(api_key=key)
        msg = await client.messages.create(
            model=model, max_tokens=8, messages=[{"role": "user", "content": "Reply OK"}]
        )
        if msg.content:
            return True, "ok"
        return False, "empty response"
    except Exception as e:
        return False, str(e)[:200]


async def probe_provider(provider: str) -> tuple[bool, str]:
    key = get_api_key(provider)
    if not key:
        _cache_set(provider, False, "missing key")
        return False, "missing key"

    if provider == "gemini":
        ok, msg = await _probe_gemini(_PROBE_MODELS["gemini"][0], key)
    elif provider == "anthropic":
        ok, msg = await _probe_anthropic(_PROBE_MODELS["anthropic"][0], key)
    elif provider == "huggingface":
        url, model = _PROBE_MODELS["huggingface"]
        ok, msg = await _probe_openai_compat("huggingface", url, model, key)
    else:
        url, model = _PROBE_MODELS[provider]
        ok, msg = await _probe_openai_compat(provider, url, model, key)

    if not ok and any(m in msg.lower() for m in _TRANSIENT_FAILURE):
        return ok, msg
    _cache_set(provider, ok, msg)
    return ok, msg


async def probe_all_providers() -> dict[str, dict]:
    from llm_providers import api_key_available, PROVIDER_KEYS

    results: dict[str, dict] = {}
    for name in PROVIDER_KEYS:
        configured = api_key_available(name)
        if not configured:
            results[name] = {"configured": False, "ok": False, "detail": "no key"}
            continue
        ok, detail = await probe_provider(name)
        results[name] = {"configured": True, "ok": ok, "detail": detail}
        logger.info("LLM probe %s: ok=%s detail=%s", name, ok, detail[:120])
    return results


async def refresh_probe_cache() -> dict[str, dict]:
    async with _probe_lock:
        return await probe_all_providers()
