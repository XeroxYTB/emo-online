#!/usr/bin/env python3
"""Configure Hugging Face Space secrets/variables for Emo Online API."""
from __future__ import annotations

import os
import sys

# SSL Windows (CERTIFICATE_VERIFY_FAILED)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "emo" / "backend"))
try:
    import ssl_fix  # noqa: F401
except ImportError:
    pass

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
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_API_KEY",
    "STRIPE_API_KEY",
    "EMERGENT_LLM_KEY",
]

VARIABLES = {
    "DB_NAME": "emo",
    "EMO_DEV_MODE": "false",
    "EMO_SERVE_FRONTEND": "false",
    "EMO_BROWSER_ENABLED": "true",
    "EMO_SKIP_STARTUP_PROBE": "true",
    "EMO_PUBLIC_BACKEND_URL": BACKEND_URL,
    "EMO_FRONTEND_URL": FRONTEND_URL,
    "CORS_ORIGINS": "https://xeroxytb.com,https://www.xeroxytb.com,https://xeroxytb.github.io,http://127.0.0.1:17841,http://localhost:17841",
    "GOOGLE_REDIRECT_URI": f"{BACKEND_URL}/api/auth/google/callback",
    "EMO_ADMIN_EMAILS": "huglostalatac@gmail.com",
    "STRIPE_BASIC_LINK": "https://buy.stripe.com/5kQ14pae7a8Rd4yb6y48001",
    "STRIPE_PREMIUM_LINK": "https://buy.stripe.com/bJe6oJbib5SBggK5Me48002",
    "STRIPE_ULTRA_LINK": "https://buy.stripe.com/4gMdRb71V3Kt8OicaC48003",
    "OPENROUTER_REFERER": FRONTEND_URL,
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
