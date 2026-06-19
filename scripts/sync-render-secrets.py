#!/usr/bin/env python3
"""Sync backend/.env vers Render.com (API gratuite 24/7)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "emo" / "backend" / ".env", override=True)

RENDER_API = "https://api.render.com/v1"
SERVICE_NAME = os.environ.get("RENDER_SERVICE_NAME", "emo-online-api")
BACKEND_URL = os.environ.get(
    "EMO_PUBLIC_BACKEND_URL", "https://xroxx-emo-online-api.hf.space"
).rstrip("/")

SECRET_KEYS = [
    "MONGO_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "GROQ_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY",
    "HF_TOKEN", "HUGGINGFACE_API_KEY", "EMERGENT_LLM_KEY",
    "STRIPE_API_KEY", "STRIPE_BASIC_LINK", "STRIPE_PREMIUM_LINK", "STRIPE_ULTRA_LINK",
    "EMO_PRODUCT_KEYS",
]

VARIABLES = {
    "DB_NAME": "emo",
    "EMO_DEV_MODE": "false",
    "EMO_SERVE_FRONTEND": "false",
    "EMO_BROWSER_ENABLED": "false",
    "EMO_USE_SALES_LLM_KEYS": "true",
    "EMO_PUBLIC_BACKEND_URL": BACKEND_URL,
    "EMO_FRONTEND_URL": "https://xeroxytb.com",
    "CORS_ORIGINS": "https://xeroxytb.com,https://www.xeroxytb.com,https://xeroxytb.github.io",
    "GOOGLE_REDIRECT_URI": f"{BACKEND_URL}/api/auth/google/callback",
    "PORT": "8010",
    "EMO_ADMIN_EMAILS": os.environ.get("EMO_ADMIN_EMAILS", "huglostalatac@gmail.com"),
}

SALES_DUP = {
    "SALES_OPENAI_API_KEY": "OPENAI_API_KEY",
    "SALES_ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
    "SALES_GEMINI_API_KEY": "GEMINI_API_KEY",
    "SALES_GROQ_API_KEY": "GROQ_API_KEY",
    "SALES_OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
    "SALES_DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
    "SALES_HF_TOKEN": "HF_TOKEN",
}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def find_service(client: httpx.Client, token: str) -> dict | None:
    cursor = None
    while True:
        params = {"limit": 20}
        if cursor:
            params["cursor"] = cursor
        r = client.get(f"{RENDER_API}/services", headers=_headers(token), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for item in data:
            svc = item.get("service") or item
            if svc.get("name") == SERVICE_NAME:
                return svc
        cursor = r.headers.get("X-Next-Cursor") or r.headers.get("x-next-cursor")
        if not cursor:
            break
    return None


def put_env(client: httpx.Client, token: str, service_id: str, key: str, value: str) -> None:
    r = client.put(
        f"{RENDER_API}/services/{service_id}/env-vars/{key}",
        headers={**_headers(token), "Content-Type": "application/json"},
        json={"value": value},
        timeout=30,
    )
    if r.status_code == 404:
        r = client.post(
            f"{RENDER_API}/services/{service_id}/env-vars",
            headers={**_headers(token), "Content-Type": "application/json"},
            json={"envVar": {"key": key, "value": value}},
            timeout=30,
        )
    r.raise_for_status()


def main() -> int:
    token = os.environ.get("RENDER_API_KEY", "").strip()
    if not token:
        print("RENDER_API_KEY manquant — crée une clé sur https://dashboard.render.com/u/settings#api-keys")
        print("Deploy 1-clic (gratuit) : https://render.com/deploy?repo=https://github.com/XeroxYTB/emo-online")
        return 1

    with httpx.Client() as client:
        svc = find_service(client, token)
        if not svc:
            print(f"Service '{SERVICE_NAME}' introuvable sur Render.")
            print("Deploy 1-clic : https://render.com/deploy?repo=https://github.com/XeroxYTB/emo-online")
            return 1

        sid = svc["id"]
        print(f"Sync env → {svc.get('name')} ({svc.get('serviceDetails', {}).get('url', BACKEND_URL)})")

        count = 0
        for key in SECRET_KEYS:
            val = os.environ.get(key, "").strip()
            if val:
                put_env(client, token, sid, key, val)
                print(f"  secret {key} OK")
                count += 1

        for key, val in VARIABLES.items():
            put_env(client, token, sid, key, val)
            print(f"  var {key} OK")
            count += 1

        for sales, src in SALES_DUP.items():
            val = os.environ.get(sales, "").strip() or os.environ.get(src, "").strip()
            if val:
                put_env(client, token, sid, sales, val)
                print(f"  sales {sales} OK")
                count += 1

        # Trigger redeploy
        dr = client.post(
            f"{RENDER_API}/services/{sid}/deploys",
            headers={**_headers(token), "Content-Type": "application/json"},
            json={"clearCache": "do_not_clear"},
            timeout=60,
        )
        if dr.status_code in (200, 201):
            print("Redeploy declenche.")
        else:
            print(f"Redeploy: HTTP {dr.status_code} (env sync OK, {count} vars)")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
