"""Tests LLM routing and fallback candidate lists."""
from __future__ import annotations

import pytest

from llm_config import resolve_model_candidates, parse_model_preference


@pytest.mark.asyncio
async def test_manual_preference_includes_fallback_chain(monkeypatch):
    monkeypatch.setattr("llm_config.api_key_available", lambda p: True)
    monkeypatch.setattr(
        "llm_health.provider_usable",
        lambda provider, configured: True,
        raising=False,
    )

    async def _fake_provider_ready(provider, model):
        from llm_config import BLOCKED_MODELS
        if (provider, model) in BLOCKED_MODELS:
            return None
        return provider, model, model

    monkeypatch.setattr("llm_config._provider_ready", _fake_provider_ready)

    cands = await resolve_model_candidates("free", "openai:gpt-4o-mini")
    assert cands[0][0] == "openai"
    assert cands[0][1] == "gpt-4o-mini"
    assert len(cands) > 1


@pytest.mark.asyncio
async def test_auto_mode_orders_groq_first(monkeypatch):
    monkeypatch.setattr("llm_config.api_key_available", lambda p: True)

    async def _fake_provider_ready(provider, model):
        return provider, model, model

    monkeypatch.setattr("llm_config._provider_ready", _fake_provider_ready)

    cands = await resolve_model_candidates("free", None)
    assert cands[0][0] == "groq"


def test_parse_model_preference():
    assert parse_model_preference("auto") is None
    assert parse_model_preference("groq:llama-3.1-8b-instant") == ("groq", "llama-3.1-8b-instant")
