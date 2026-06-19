#!/usr/bin/env python3
"""Sync backend/.env vers Koyeb service (gratuit, sans carte)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "emo" / "backend" / ".env", override=True)

APP = os.environ.get("KOYEB_APP", "emo-online")
SERVICE = os.environ.get("KOYEB_SERVICE", "emo-online-api")
BACKEND = os.environ.get("EMO_PUBLIC_BACKEND_URL", f"https://{SERVICE}-{os.environ.get('KOYEB_ORG', 'user')}.koyeb.app").rstrip("/")

SECRETS = [
    "MONGO_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "GROQ_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY",
    "HF_TOKEN", "HUGGINGFACE_API_KEY", "EMERGENT_LLM_KEY",
    "STRIPE_API_KEY", "STRIPE_BASIC_LINK", "STRIPE_PREMIUM_LINK", "STRIPE_ULTRA_LINK",
    "EMO_PRODUCT_KEYS",
]

VARS = {
    "DB_NAME": "emo",
    "EMO_DEV_MODE": "false",
    "EMO_SERVE_FRONTEND": "false",
    "EMO_BROWSER_ENABLED": "false",
    "EMO_USE_SALES_LLM_KEYS": "true",
    "EMO_PUBLIC_BACKEND_URL": BACKEND,
    "EMO_FRONTEND_URL": "https://xeroxytb.com",
    "CORS_ORIGINS": "https://xeroxytb.com,https://www.xeroxytb.com,https://xeroxytb.github.io",
    "GOOGLE_REDIRECT_URI": f"{BACKEND}/api/auth/google/callback",
    "PORT": "8010",
    "EMO_ADMIN_EMAILS": os.environ.get("EMO_ADMIN_EMAILS", "huglostalatac@gmail.com"),
}

SALES = {
    "SALES_OPENAI_API_KEY": "OPENAI_API_KEY",
    "SALES_ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
    "SALES_GEMINI_API_KEY": "GEMINI_API_KEY",
    "SALES_GROQ_API_KEY": "GROQ_API_KEY",
    "SALES_OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
    "SALES_DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
    "SALES_HF_TOKEN": "HF_TOKEN",
}


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def main() -> int:
    token = os.environ.get("KOYEB_TOKEN", "").strip()
    if not token:
        print("KOYEB_TOKEN manquant")
        print("1. Cree un compte sur https://app.koyeb.com (gratuit, sans carte)")
        print("2. Settings > API > Create token")
        print("3. Ajoute KOYEB_TOKEN=... dans emo/backend/.env")
        return 1

    env = os.environ.copy()
    env["KOYEB_TOKEN"] = token

    # Verifier service
    st = run(["koyeb", "service", "list", "-o", "json"])
    if st.returncode != 0:
        print(st.stderr or st.stdout)
        return 1

    pairs: list[str] = []
    for k in SECRETS:
        v = os.environ.get(k, "").strip()
        if v:
            pairs.append(f"{k}={v}")
    for k, v in VARS.items():
        pairs.append(f"{k}={v}")
    for sales, src in SALES.items():
        v = os.environ.get(sales, "").strip() or os.environ.get(src, "").strip()
        if v:
            pairs.append(f"{sales}={v}")

    cmd = ["koyeb", "service", "update", f"{APP}/{SERVICE}", "--env"] + pairs
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        return r.returncode
    print("Koyeb env sync OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
