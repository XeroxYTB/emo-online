"""OAuth account connections — GitHub, Google, etc. (tokens server-side only).

Required env vars (see .env.example):
  GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET — GitHub OAuth App
  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET — reused from login; add redirect URI:
    {EMO_PUBLIC_BACKEND_URL}/api/oauth/google/callback
"""
from __future__ import annotations

import ssl_fix  # noqa: F401

import base64
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

# --- Provider registry -------------------------------------------------------

PROVIDER_IDS = ("github", "google")

PROVIDERS: dict[str, dict[str, Any]] = {
    "github": {
        "label": "GitHub",
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scopes": ["read:user", "repo", "read:org"],
        "redirect_path": "/api/oauth/github/callback",
        "profile_url": "https://api.github.com/user",
    },
    "google": {
        "label": "Google",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        "redirect_path": "/api/oauth/google/callback",
        "profile_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "access_type": "offline",
        "prompt": "consent",
    },
}


def _public_backend_url() -> str:
    return os.environ.get("EMO_PUBLIC_BACKEND_URL", "https://xroxx-emo-online-api.hf.space").rstrip("/")


def _frontend_url() -> str:
    return os.environ.get("EMO_FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")


def redirect_uri(provider: str) -> str:
    explicit = os.environ.get(f"{provider.upper()}_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    cfg = PROVIDERS.get(provider) or {}
    path = cfg.get("redirect_path", f"/api/oauth/{provider}/callback")
    return f"{_public_backend_url()}{path}"


def is_provider_configured(provider: str) -> bool:
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return False
    cid = os.environ.get(cfg["client_id_env"], "").strip()
    secret = os.environ.get(cfg["client_secret_env"], "").strip()
    return bool(cid and secret)


def normalize_return_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        return f"{_frontend_url()}/auth/connections/callback"
    if url.endswith("/auth/connections/callback"):
        return url
    return f"{url}/auth/connections/callback"


def encode_state(user_id: str, return_url: str) -> str:
    payload = {"user_id": user_id, "return": normalize_return_url(return_url)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


def decode_state(state: str) -> tuple[Optional[str], str]:
    try:
        pad = "=" * (-len(state) % 4)
        data = json.loads(base64.urlsafe_b64decode(state + pad).decode())
        user_id = data.get("user_id")
        return user_id, normalize_return_url(data.get("return") or "")
    except Exception:
        return None, normalize_return_url("")


def build_authorize_url(provider: str, user_id: str, return_url: str) -> str:
    cfg = PROVIDERS[provider]
    client_id = os.environ[cfg["client_id_env"]]
    state = encode_state(user_id, return_url)
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider),
        "state": state,
    }
    if provider == "github":
        params["scope"] = " ".join(cfg["scopes"])
    else:
        params["response_type"] = "code"
        params["scope"] = " ".join(cfg["scopes"])
        params["access_type"] = cfg.get("access_type", "offline")
        params["prompt"] = cfg.get("prompt", "consent")
    return f"{cfg['auth_url']}?{urlencode(params)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at_from_token(token_data: dict) -> Optional[str]:
    expires_in = token_data.get("expires_in")
    if expires_in is None:
        return None
    try:
        dt = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        return dt.isoformat()
    except (TypeError, ValueError):
        return None


async def exchange_code(provider: str, code: str) -> dict:
    cfg = PROVIDERS[provider]
    client_id = os.environ[cfg["client_id_env"]]
    client_secret = os.environ[cfg["client_secret_env"]]
    async with httpx.AsyncClient(timeout=25) as client:
        if provider == "github":
            resp = await client.post(
                cfg["token_url"],
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri(provider),
                },
            )
        else:
            resp = await client.post(
                cfg["token_url"],
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri(provider),
                    "grant_type": "authorization_code",
                },
            )
        if resp.status_code != 200:
            raise ValueError(f"Token exchange failed: {resp.text[:300]}")
        data = resp.json()
        if provider == "github" and data.get("error"):
            raise ValueError(data.get("error_description") or data.get("error"))
        return data


async def fetch_profile(provider: str, access_token: str) -> dict:
    cfg = PROVIDERS[provider]
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    if provider == "github":
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(cfg["profile_url"], headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Profile fetch failed: {resp.text[:200]}")
        raw = resp.json()
    if provider == "github":
        login = raw.get("login") or ""
        return {
            "login": login,
            "name": raw.get("name") or login,
            "email": raw.get("email"),
            "avatar_url": raw.get("avatar_url"),
            "display": login or raw.get("name") or "GitHub",
        }
    email = raw.get("email") or ""
    name = raw.get("name") or email.split("@")[0]
    return {
        "login": email,
        "name": name,
        "email": email,
        "avatar_url": raw.get("picture"),
        "display": email or name or "Google",
    }


def public_account_row(provider: str, doc: Optional[dict]) -> dict:
    configured = is_provider_configured(provider)
    cfg = PROVIDERS[provider]
    row = {
        "provider": provider,
        "label": cfg["label"],
        "configured": configured,
        "connected": bool(doc),
        "profile": None,
        "scopes": doc.get("scopes") if doc else cfg["scopes"],
        "connected_at": doc.get("connected_at") if doc else None,
    }
    if not configured:
        row["message"] = "Configure keys on server"
    if doc and doc.get("profile"):
        prof = doc["profile"]
        row["profile"] = {
            "login": prof.get("login"),
            "name": prof.get("name"),
            "display": prof.get("display") or prof.get("login") or prof.get("name"),
            "avatar_url": prof.get("avatar_url"),
        }
    return row


async def list_public_accounts(db, user_id: str) -> list[dict]:
    cursor = db.connected_accounts.find({"user_id": user_id}, {"_id": 0})
    by_provider = {row["provider"]: row async for row in cursor}
    return [public_account_row(p, by_provider.get(p)) for p in PROVIDER_IDS]


async def get_account_token(db, user_id: str, provider: str) -> Optional[str]:
    doc = await db.connected_accounts.find_one(
        {"user_id": user_id, "provider": provider},
        {"_id": 0, "access_token": 1, "expires_at": 1, "refresh_token": 1},
    )
    if not doc:
        return None
    token = doc.get("access_token")
    if not token:
        return None
    expires_at = doc.get("expires_at")
    if expires_at and provider == "google":
        if isinstance(expires_at, str):
            exp = datetime.fromisoformat(expires_at)
        else:
            exp = expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc) + timedelta(seconds=30):
            refreshed = await refresh_google_token(db, user_id, doc.get("refresh_token"))
            if refreshed:
                return refreshed
            return None
    return token


async def refresh_google_token(db, user_id: str, refresh_token: Optional[str]) -> Optional[str]:
    if not refresh_token or not is_provider_configured("google"):
        return None
    cfg = PROVIDERS["google"]
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            cfg["token_url"],
            data={
                "client_id": os.environ[cfg["client_id_env"]],
                "client_secret": os.environ[cfg["client_secret_env"]],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        return None
    update = {
        "access_token": access_token,
        "updated_at": _now_iso(),
        "expires_at": _expires_at_from_token(data),
    }
    if data.get("refresh_token"):
        update["refresh_token"] = data["refresh_token"]
    await db.connected_accounts.update_one(
        {"user_id": user_id, "provider": "google"},
        {"$set": update},
    )
    return access_token


async def store_connection(db, user_id: str, provider: str, token_data: dict, profile: dict) -> None:
    cfg = PROVIDERS[provider]
    doc = {
        "user_id": user_id,
        "provider": provider,
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "scopes": cfg["scopes"],
        "expires_at": _expires_at_from_token(token_data),
        "profile": profile,
        "updated_at": _now_iso(),
    }
    existing = await db.connected_accounts.find_one({"user_id": user_id, "provider": provider})
    if existing:
        doc["connected_at"] = existing.get("connected_at") or _now_iso()
    else:
        doc["connected_at"] = _now_iso()
    await db.connected_accounts.update_one(
        {"user_id": user_id, "provider": provider},
        {"$set": doc},
        upsert=True,
    )


async def disconnect_account(db, user_id: str, provider: str) -> bool:
    result = await db.connected_accounts.delete_one({"user_id": user_id, "provider": provider})
    return result.deleted_count > 0


async def github_api(
    access_token: str,
    method: str,
    path: str,
    *,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
) -> dict:
    """Authenticated GitHub REST API call using the user's token."""
    path = (path or "").strip()
    if not path:
        return {"ok": False, "error": "path missing"}
    if path.startswith("http"):
        url = path
    else:
        url = f"https://api.github.com/{path.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method.upper(),
                url,
                headers=headers,
                params=params,
                json=json_body,
            )
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "error": resp.text[:500]}
        if resp.status_code == 204:
            return {"ok": True, "status": 204}
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:8000]
        return {"ok": True, "status": resp.status_code, "data": body}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def github_search_authenticated(query: str, access_token: str, limit: int = 8) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query missing"}
    limit = min(max(limit, 1), 30)
    result = await github_api(
        access_token,
        "GET",
        "search/repositories",
        params={"q": q, "per_page": str(limit), "sort": "stars"},
    )
    if not result.get("ok"):
        return result
    items = (result.get("data") or {}).get("items") or []
    rows = []
    for i, repo in enumerate(items[:limit], 1):
        rows.append({
            "rank": i,
            "title": repo.get("full_name") or repo.get("name"),
            "url": repo.get("html_url"),
            "snippet": (repo.get("description") or "")[:240],
            "stars": repo.get("stargazers_count"),
            "language": repo.get("language"),
        })
    return {"ok": True, "query": q, "source": "github_api", "results": rows, "count": len(rows)}
