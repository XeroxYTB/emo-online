"""Tests routage vision (Groq / Gemini gratuits uniquement)."""
from __future__ import annotations

import pytest

from llm_config import (
    BLOCKED_MODELS,
    FREE_VISION_CATALOG,
    resolve_free_vision_candidates,
    vision_keys_missing_message,
)
from llm_providers import api_key_available

_DECOMMISSIONED_GROQ_VISION = {
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview",
}


def test_free_vision_catalog_uses_current_groq_models():
    groq_models = {e["model"] for e in FREE_VISION_CATALOG if e["provider"] == "groq"}
    assert "meta-llama/llama-4-scout-17b-16e-instruct" in groq_models
    assert groq_models.isdisjoint(_DECOMMISSIONED_GROQ_VISION)
    for model in _DECOMMISSIONED_GROQ_VISION:
        assert ("groq", model) in BLOCKED_MODELS


def test_api_key_available_checks_sales_groq(monkeypatch):
    monkeypatch.setenv("EMO_USE_SALES_LLM_KEYS", "true")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("SALES_GROQ_API_KEY", "gsk_test_sales_key")
    assert api_key_available("groq") is True


def test_api_key_available_checks_sales_gemini(monkeypatch):
    monkeypatch.setenv("EMO_USE_SALES_LLM_KEYS", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("SALES_GEMINI_API_KEY", "AIza_test")
    assert api_key_available("gemini") is True


@pytest.mark.asyncio
async def test_resolve_free_vision_with_sales_keys(monkeypatch):
    monkeypatch.setenv("EMO_USE_SALES_LLM_KEYS", "true")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("SALES_GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("SALES_GEMINI_API_KEY", "AIza_test")

    cands = await resolve_free_vision_candidates()
    providers = {c[0] for c in cands}
    assert "groq" in providers
    assert "gemini" in providers
    assert all(p in ("groq", "gemini") for p in providers)


def test_vision_keys_missing_message_lists_env_vars(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("SALES_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("SALES_GEMINI_API_KEY", raising=False)
    msg = vision_keys_missing_message()
    assert "GROQ_API_KEY" in msg
    assert "GEMINI_API_KEY" in msg
