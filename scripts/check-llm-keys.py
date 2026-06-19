#!/usr/bin/env python3
"""Affiche quelles clés LLM sont configurées (local .env + optionnel prod)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "emo" / "backend" / ".env", override=True)

PROVIDERS = {
    "groq": ["GROQ_API_KEY"],
    "huggingface": ["HF_TOKEN", "HUGGINGFACE_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY", "EMERGENT_LLM_KEY"],
}

LABELS = {
    "groq": "Groq (gratuit, rapide)",
    "huggingface": "Hugging Face Router (gratuit)",
    "openrouter": "OpenRouter (modèles free + payants)",
    "deepseek": "DeepSeek (Chat + R1)",
    "openai": "OpenAI / ChatGPT",
    "gemini": "Google Gemini",
    "anthropic": "Anthropic / Claude",
}


def has_key(env_names: list[str]) -> bool:
    return any(os.environ.get(k, "").strip() for k in env_names)


def main() -> int:
    print("=== Clés LLM — emo/backend/.env ===\n")
    missing_priority = []
    for name, keys in PROVIDERS.items():
        ok = has_key(keys)
        mark = "OK" if ok else "MANQUANT"
        print(f"  [{mark:8}] {name:12} — {LABELS[name]}")
        if not ok and name in ("openrouter", "deepseek", "groq", "huggingface"):
            missing_priority.append(name)

    if missing_priority:
        print("\n→ Priorité pour débloquer tous les modèles :")
        for p in missing_priority:
            print(f"   - {p}")

    prod = os.environ.get("EMO_PUBLIC_BACKEND_URL", "https://xroxx-emo-online-api.hf.space").rstrip("/")
    try:
        with urllib.request.urlopen(f"{prod}/api/llm/status", timeout=20) as resp:
            data = json.loads(resp.read().decode())
        print(f"\n=== Prod ({prod}) ===\n")
        live = data.get("live") or {}
        for name in PROVIDERS:
            configured = data.get(name, False)
            row = live.get(name) or {}
            live_ok = row.get("ok")
            detail = (row.get("detail") or "")[:80]
            if not configured:
                st = "pas de clé"
            elif live_ok is True:
                st = "live OK"
            elif live_ok is False:
                st = f"live KO — {detail}"
            else:
                st = "clé présente"
            print(f"  {name:12} {st}")
    except Exception as e:
        print(f"\n(Prod inaccessible: {e})")

    print("\nPour ajouter les clés : scripts\\setup-llm-keys.ps1")
    print("Puis sync HF : scripts\\sync-hf-secrets.bat")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
