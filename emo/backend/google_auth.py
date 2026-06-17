"""Google OAuth 2.0 — connexion self-hosted (sans Emergent)."""
from __future__ import annotations

import ssl_fix  # noqa: F401

import base64
import json
import os
from urllib.parse import urlencode

import httpx

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def has_client_id() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID", "").strip())


def is_configured() -> bool:
    return has_client_id() and bool(os.environ.get("GOOGLE_CLIENT_SECRET", "").strip())


def redirect_uri() -> str:
    explicit = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    base = os.environ.get("EMO_PUBLIC_BACKEND_URL", "http://127.0.0.1:8010").rstrip("/")
    return f"{base}/api/auth/google/callback"


def normalize_frontend_callback(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        return "http://127.0.0.1:3000/auth/google/callback"
    if url.endswith("/auth/google/callback"):
        return url
    if url.endswith("/chat"):
        return url[: -len("/chat")] + "/auth/google/callback"
    if url.endswith("/login"):
        return url[: -len("/login")] + "/auth/google/callback"
    return f"{url}/auth/google/callback"


def build_login_url(frontend_redirect: str, desktop: bool = False) -> str:
    state = base64.urlsafe_b64encode(
        json.dumps({"redirect": frontend_redirect}).encode()
    ).decode().rstrip("=")
    params = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "state": state,
    }
    if desktop:
        pass
    else:
        params["prompt"] = "select_account"
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def parse_state(state: str) -> str:
    try:
        pad = "=" * (-len(state) % 4)
        data = json.loads(base64.urlsafe_b64decode(state + pad).decode())
        return normalize_frontend_callback(data.get("redirect") or "")
    except Exception:
        return "http://127.0.0.1:3000/auth/google/callback"


def map_oauth_error(error: str, detail: str = "") -> str:
    if error == "access_denied":
        return "access_denied"
    if "redirect_uri_mismatch" in detail:
        return "redirect_uri_mismatch"
    if "invalid_client" in detail:
        return "invalid_client"
    return error or "google_auth_failed"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            detail = token_resp.text[:300]
            if "invalid_client" in detail:
                raise ValueError("invalid_client")
            if "redirect_uri_mismatch" in detail:
                raise ValueError("redirect_uri_mismatch")
            raise ValueError(f"Token Google invalide: {detail}")
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise ValueError("Pas de access_token Google")

        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            raise ValueError("Impossible de lire le profil Google")
        return user_resp.json()


async def verify_id_token(id_token: str) -> dict:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise ValueError("missing_client_id")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )
    if resp.status_code != 200:
        raise ValueError("invalid_id_token")
    data = resp.json()
    aud = data.get("aud") or data.get("azp")
    if aud != client_id:
        raise ValueError("wrong_audience")
    if not data.get("email"):
        raise ValueError("no_email")
    if str(data.get("email_verified", "true")).lower() == "false":
        raise ValueError("email_not_verified")
    return data
