#!/usr/bin/env python3
"""Configure Hugging Face Space secrets/variables for Emo Online API."""
from __future__ import annotations

import os
import sys

from huggingface_hub import HfApi

REPO_ID = os.environ.get("HF_SPACE_REPO", "Xroxx/emo-online-api")
BACKEND_URL = os.environ.get(
    "EMO_PUBLIC_BACKEND_URL", "https://xroxx-emo-online-api.hf.space"
)
FRONTEND_URL = "https://xeroxytb.com"

SECRETS = [
    "MONGO_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "STRIPE_API_KEY",
]

VARIABLES = {
    "DB_NAME": "emo",
    "EMO_DEV_MODE": "false",
    "EMO_SERVE_FRONTEND": "false",
    "EMO_PUBLIC_BACKEND_URL": BACKEND_URL,
    "EMO_FRONTEND_URL": FRONTEND_URL,
    "CORS_ORIGINS": "https://xeroxytb.com,https://www.xeroxytb.com,https://xeroxytb.github.io",
    "PORT": "8010",
    "EMO_ADMIN_EMAILS": "huglostalatac@gmail.com",
    "STRIPE_BASIC_LINK": "https://buy.stripe.com/5kQ14pae7a8Rd4yb6y48001",
    "STRIPE_PREMIUM_LINK": "https://buy.stripe.com/bJe6oJbib5SBggK5Me48002",
    "STRIPE_ULTRA_LINK": "https://buy.stripe.com/4gMdRb71V3Kt8OicaC48003",
}


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("HF_TOKEN manquant", file=sys.stderr)
        return 1

    api = HfApi(token=token)
    print(f"Configuring {REPO_ID}...")

    for key in SECRETS:
        val = os.environ.get(key, "").strip()
        if not val:
            print(f"  skip secret {key} (empty)")
            continue
        api.add_space_secret(repo_id=REPO_ID, key=key, value=val)
        print(f"  secret {key} OK")

    for key, val in VARIABLES.items():
        api.add_space_variable(repo_id=REPO_ID, key=key, value=val)
        print(f"  variable {key} OK")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
