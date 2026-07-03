"""Émo — Hugo's personal AI backend with local agent control + long-term memory."""
import ssl_fix  # noqa: F401 — certificats SSL Windows avant httpx/anthropic

import hashlib
import os
import json
import uuid
import logging
import asyncio
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

import io
import zipfile
import httpx
import bcrypt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks, Query, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from starlette.middleware.cors import CORSMiddleware

from emergentintegrations.llm.chat import (
    LlmChat, UserMessage, TextDelta, ToolCallReady, ToolCallStart, StreamDone
)
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse,
)

from emo_prompts import build_system_prompt, build_compact_system_prompt, EMO_TOOLS, MEMORY_EXTRACTION_PROMPT, UNCENSORED_SYSTEM_APPEND, VISION_PRECISION_PROMPT
from emo_self_edit import (
    EMO_SELF_TOOLS,
    emo_read_self,
    emo_edit_self,
    emo_list_self_saves,
    emo_restore_self,
    emo_reflect,
    emo_remember,
    emo_introspect,
    get_identity_overrides,
)
from browser_control import (
    BROWSER_CONTROL_TOOLS,
    BROWSER_CONTROL_TOOL_NAMES,
    browser_open as do_browser_open,
    browser_snapshot as do_browser_snapshot,
    browser_click as do_browser_click,
    browser_type as do_browser_type,
    browser_fill as do_browser_fill,
    browser_scroll as do_browser_scroll,
    browser_press as do_browser_press,
    browser_keyboard as do_browser_keyboard,
    browser_close as do_browser_close,
)
from agent_relay import registry as agent_registry
from web_tools import (
    web_search as do_web_search,
    web_fetch as do_web_fetch,
    web_fetch_json as do_web_fetch_json,
    browser_visit as do_browser_visit,
    get_datetime as do_get_datetime,
    github_search as do_github_search,
    github_api as do_github_api,
    stackoverflow_search as do_stackoverflow_search,
    calculate_expression as do_calculate,
    WEB_TOOLS,
)
from llm_config import (
    SUBSCRIPTION_PLANS, get_user_tier, resolve_model, resolve_model_candidates, models_for_tier, plans_for_api,
    parse_client_reference, tier_allows_local_agent, TIER_RANK, PAID_TIERS,
    stripe_link_for_tier, resolve_free_vision_candidates, vision_keys_missing_message,
)
import google_auth
import connected_accounts as conn_accounts
from image_tools import generate_image as do_generate_image, GENERATE_IMAGE_TOOL
from site_intent import is_full_site_request, resolve_site_output_dir
from site_builder import build_sales_site
from llm_health import refresh_probe_cache, mark_provider_ok, mark_provider_failed


def _safe_mark_provider_ok(provider: str) -> None:
    try:
        mark_provider_ok(provider)
    except Exception:
        pass


def _safe_mark_provider_failed(provider: str, reason: str = "") -> None:
    try:
        mark_provider_failed(provider, reason)
    except Exception:
        pass
from hf_models import refresh_hf_catalog, is_uncensored_model
from llm_providers import providers_status, configured_providers, api_key_available
from tool_router import select_tools_for_message
from open_site_intent import resolve_open_site_url, is_simple_open_request, open_site_label
from product_keys import (
    ensure_product_keys_seeded,
    create_product_keys,
    redeem_product_key,
    is_commercial_license,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get('EMO_ADMIN_EMAILS', 'hugo@example.com,huglostalatac@gmail.com').split(',') if e.strip()}
STRIPE_PAYMENT_LINK = os.environ.get('STRIPE_PAYMENT_LINK', '')
STRIPE_SUBSCRIPTION_LINK = os.environ.get('STRIPE_SUBSCRIPTION_LINK', '')
STRIPE_BASIC_LINK = os.environ.get('STRIPE_BASIC_LINK', 'https://buy.stripe.com/5kQ14pae7a8Rd4yb6y48001')
STRIPE_PREMIUM_LINK = os.environ.get('STRIPE_PREMIUM_LINK', '')
STRIPE_ULTRA_LINK = os.environ.get('STRIPE_ULTRA_LINK', '')
EMO_PUBLIC_BACKEND_URL = os.environ.get('EMO_PUBLIC_BACKEND_URL', 'http://127.0.0.1:8001').rstrip('/')


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw and raw != "*":
        return [o.strip() for o in raw.split(",") if o.strip()]
    front = os.environ.get("EMO_FRONTEND_URL", "").strip().rstrip("/")
    if front:
        from urllib.parse import urlparse
        u = urlparse(front)
        origin = f"{u.scheme}://{u.netloc}"
        return [origin]
    return [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8010",
        "http://localhost:8010",
        "http://127.0.0.1:17841",
        "http://localhost:17841",
        "https://xeroxytb.com",
        "https://www.xeroxytb.com",
        "https://xeroxytb.github.io",
    ]


# License config — €15/month subscription
DAILY_MESSAGES = 10  # free trial quota per day for non-subscribers
LICENSE_PRICE_EUR = float(os.environ.get('LICENSE_PRICE_EUR', '15.00'))
LICENSE_CURRENCY = "eur"
LICENSE_INTERVAL = os.environ.get('LICENSE_INTERVAL', 'month')  # "month" or "lifetime"
SUBSCRIPTION_PERIOD_DAYS = int(os.environ.get('SUBSCRIPTION_PERIOD_DAYS', '31'))  # grace days per paid period

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# --- Runtime-overridable settings ---
# These keys live in MongoDB (collection `app_settings`, single doc `_id="config"`).
# Admin can PATCH them via /api/admin/settings without restarting the backend.
SETTING_KEYS = {
    "stripe_payment_link": str,
    "stripe_subscription_link": str,
    "stripe_basic_link": str,
    "stripe_premium_link": str,
    "stripe_ultra_link": str,
    "license_price_eur": float,
    "license_interval": str,
    "daily_messages": int,
    "subscription_period_days": int,
}
_SETTINGS_CACHE: dict = {}

async def _load_settings():
    """Load settings doc and merge over env defaults into _SETTINGS_CACHE."""
    global _SETTINGS_CACHE
    doc = await db.app_settings.find_one({"_id": "config"}) or {}
    _SETTINGS_CACHE = {
        "stripe_payment_link": doc.get("stripe_payment_link") or STRIPE_PAYMENT_LINK,
        "stripe_subscription_link": doc.get("stripe_subscription_link") or STRIPE_SUBSCRIPTION_LINK,
        "stripe_basic_link": doc.get("stripe_basic_link") or STRIPE_BASIC_LINK,
        "stripe_premium_link": doc.get("stripe_premium_link") or STRIPE_PREMIUM_LINK,
        "stripe_ultra_link": doc.get("stripe_ultra_link") or STRIPE_ULTRA_LINK,
        "license_price_eur": float(doc.get("license_price_eur") if doc.get("license_price_eur") is not None else LICENSE_PRICE_EUR),
        "license_interval": doc.get("license_interval") or LICENSE_INTERVAL,
        "daily_messages": int(doc.get("daily_messages") if doc.get("daily_messages") is not None else DAILY_MESSAGES),
        "subscription_period_days": int(doc.get("subscription_period_days") if doc.get("subscription_period_days") is not None else SUBSCRIPTION_PERIOD_DAYS),
    }
    for key in ("stripe_basic_link", "stripe_premium_link", "stripe_ultra_link"):
        val = _SETTINGS_CACHE.get(key) or ""
        if val:
            env_key = {"stripe_basic_link": "STRIPE_BASIC_LINK", "stripe_premium_link": "STRIPE_PREMIUM_LINK", "stripe_ultra_link": "STRIPE_ULTRA_LINK"}[key]
            os.environ[env_key] = str(val)
    for env_name, val in (doc.get("llm_keys") or {}).items():
        if val:
            os.environ[str(env_name)] = str(val)


LLM_ADMIN_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "huggingface": "HF_TOKEN",
}


def _mask_secret(val: str) -> str:
    v = (val or "").strip()
    if not v:
        return ""
    if len(v) <= 8:
        return "••••"
    return f"{v[:4]}…{v[-4:]}"

def s(key: str):
    """Return current runtime setting (env default if not loaded yet)."""
    if not _SETTINGS_CACHE:
        # Sync fallback in case a request hits before startup hook completes
        return {
            "stripe_payment_link": STRIPE_PAYMENT_LINK,
            "stripe_subscription_link": STRIPE_SUBSCRIPTION_LINK,
            "stripe_basic_link": STRIPE_BASIC_LINK,
            "stripe_premium_link": STRIPE_PREMIUM_LINK,
            "stripe_ultra_link": STRIPE_ULTRA_LINK,
            "license_price_eur": LICENSE_PRICE_EUR,
            "license_interval": LICENSE_INTERVAL,
            "daily_messages": DAILY_MESSAGES,
            "subscription_period_days": SUBSCRIPTION_PERIOD_DAYS,
        }.get(key)
    return _SETTINGS_CACHE.get(key)

app = FastAPI(title="Émo API")
api = APIRouter(prefix="/api")

async def _ensure_admin_password_users() -> None:
    """Ensure admin emails can log in with password (seed doc passwords if missing)."""
    seeds = [
        ("hugo@example.com", "emo-test-2026", "Hugo"),
        ("huglostalatac@gmail.com", "emo2026", "Hugo"),
    ]
    for email, password, name in seeds:
        if email.lower() not in ADMIN_EMAILS:
            continue
        try:
            existing = await db.users.find_one({"email": email}, {"_id": 0})
            pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if existing:
                await db.users.update_one(
                    {"email": email},
                    {"$set": {"password_hash": pwd_hash, "auth_provider": existing.get("auth_provider") or "password"}},
                )
                user_id = existing["user_id"]
                logger.info("Admin password ensured for %s", email)
            else:
                doc = make_user_doc(email, name, None, "password")
                doc["password_hash"] = pwd_hash
                await db.users.insert_one(doc)
                user_id = doc["user_id"]
                logger.info("Admin user created: %s", email)
            await db.licenses.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "paid": True,
                        "status": "active",
                        "interval": "lifetime",
                        "paid_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "$setOnInsert": {"user_id": user_id, "daily_count": 0, "daily_day": ""},
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("Admin seed failed for %s: %s", email, exc)


@app.on_event("startup")
async def _settings_startup():
    async def _boot():
        await _load_settings()
        seeded = await ensure_product_keys_seeded(db)
        if seeded:
            logger.info("Product keys seeded from EMO_PRODUCT_KEYS: %d", seeded)
        llm_ok = configured_providers()
        logger.info("App settings loaded: %s", _SETTINGS_CACHE)
        logger.info(
            "Google OAuth: %s | LLM cloud: %s",
            "OK" if google_auth.has_client_id() else "non configuré",
            ", ".join(llm_ok) if llm_ok else "aucune clé (.env)",
        )
        if os.environ.get("EMO_SKIP_STARTUP_PROBE", "").lower() not in ("1", "true", "yes"):
            asyncio.create_task(refresh_probe_cache())
        if api_key_available("huggingface"):
            asyncio.create_task(refresh_hf_catalog())
        await _ensure_admin_password_users()

    asyncio.create_task(_boot())

logger = logging.getLogger("emo")
logging.basicConfig(level=logging.INFO)


# ============================ MODELS ============================ #

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    auth_provider: str
    created_at: datetime


class GoogleVerifyBody(BaseModel):
    credential: str


class SignupBody(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class CreateConversationBody(BaseModel):
    title: Optional[str] = "Nouvelle conversation"
    mode: Optional[str] = "tech"


class RenameConversationBody(BaseModel):
    title: str


class SendMessageBody(BaseModel):
    conversation_id: str
    content: str
    mode: Optional[str] = "tech"
    model_preference: Optional[str] = "auto"
    use_agent_tools: Optional[bool] = True
    images: Optional[List[str]] = None  # base64 JPEG/PNG sans préfixe data:
    image_media_types: Optional[List[str]] = None  # mime par image (image/jpeg, image/png, …)


class MemoryBody(BaseModel):
    content: str


# ============================ AUTH HELPERS ============================ #

async def get_session_token_from_request(request: Request) -> Optional[str]:
    token = request.cookies.get("session_token")
    if token:
        return token
    header = request.headers.get("x-emo-session", "").strip()
    if header:
        return header
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


async def resolve_user_from_token(token: Optional[str]) -> Optional[User]:
    if not token:
        return None
    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        return None
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        return None
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return User(**user_doc)


async def get_current_user(request: Request) -> User:
    token = await get_session_token_from_request(request)
    user = await resolve_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    return user


def set_session_cookie(response: Response, token: str):
    dev = os.environ.get("EMO_DEV_MODE", "").lower() in ("1", "true", "yes")
    response.set_cookie(
        key="session_token", value=token, max_age=7 * 24 * 60 * 60,
        httponly=True, secure=not dev, samesite="lax" if dev else "none", path="/",
    )


def make_user_doc(email: str, name: str, picture: Optional[str], provider: str) -> dict:
    return {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": email, "name": name, "picture": picture,
        "auth_provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def create_session(user_id: str, token: Optional[str] = None) -> str:
    token = token or f"sess_{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "session_token": token, "user_id": user_id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return token


async def create_oauth_exchange(user_id: str) -> str:
    token = f"gx_{uuid.uuid4().hex}"
    await db.oauth_exchanges.insert_one({
        "token": token,
        "user_id": user_id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "used": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return token


async def consume_oauth_exchange(exchange_token: str) -> Optional[str]:
    doc = await db.oauth_exchanges.find_one({"token": exchange_token, "used": False}, {"_id": 0})
    if not doc:
        return None
    expires_at = doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    await db.oauth_exchanges.update_one({"token": exchange_token}, {"$set": {"used": True}})
    return doc["user_id"]


# ============================ AUTH ROUTES ============================ #

@api.post("/auth/signup")
async def signup(body: SignupBody, response: Response):
    if await db.users.find_one({"email": body.email}, {"_id": 0}):
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    doc = make_user_doc(body.email, body.name, None, "password")
    doc["password_hash"] = pwd_hash
    await db.users.insert_one(doc)
    token = await create_session(doc["user_id"])
    set_session_cookie(response, token)
    return {"user_id": doc["user_id"], "email": doc["email"], "name": doc["name"], "picture": None, "session_token": token}


@api.post("/auth/login")
async def login(body: LoginBody, response: Response):
    user = await db.users.find_one({"email": body.email}, {"_id": 0})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    token = await create_session(user["user_id"])
    set_session_cookie(response, token)
    return {
        "user_id": user["user_id"], "email": user["email"], "name": user["name"],
        "picture": user.get("picture"), "session_token": token,
    }


@api.get("/auth/google/status")
async def google_auth_status():
    has_id = google_auth.has_client_id()
    redirect_ready = google_auth.is_configured()
    frontend = os.environ.get("EMO_FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
    return {
        "configured": has_id,
        "redirect_ready": redirect_ready,
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", "").strip() if has_id else None,
        "redirect_uri": google_auth.redirect_uri() if redirect_ready else None,
        "frontend_callback": f"{frontend}/auth/google/callback",
        "setup": None if has_id else {
            "console_url": "https://console.cloud.google.com/apis/credentials",
            "javascript_origins": [
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "http://127.0.0.1:8010",
                "https://xeroxytb.com",
                "https://www.xeroxytb.com",
                "https://xeroxytb.github.io",
            ],
            "redirect_uris": [google_auth.redirect_uri()],
            "script": "tools/setup-google-oauth.ps1",
        },
    }


@api.post("/auth/google/verify")
async def google_verify(body: GoogleVerifyBody, response: Response):
    if not google_auth.has_client_id():
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID manquant dans backend/.env")
    try:
        profile = await google_auth.verify_id_token(body.credential)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"Google: {exc}")
    email = profile.get("email")
    name = profile.get("name") or email.split("@")[0]
    picture = profile.get("picture")
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {
            "name": name or existing.get("name"),
            "picture": picture or existing.get("picture"),
            "auth_provider": "google",
        }})
    else:
        doc = make_user_doc(email, name, picture, "google")
        await db.users.insert_one(doc)
        user_id = doc["user_id"]
    await _get_or_init_license(user_id, email=email)
    session_token = await create_session(user_id)
    set_session_cookie(response, session_token)
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "auth_provider": "google",
        "session_token": session_token,
    }


@api.get("/auth/google/login")
async def google_login(
    redirect: str = Query(default="http://127.0.0.1:3000/auth/google/callback"),
    desktop: bool = Query(default=False),
):
    if not google_auth.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth non configuré. Lance tools\\setup-google-oauth.ps1 ou ajoute GOOGLE_CLIENT_ID/SECRET dans backend/.env",
        )
    target = google_auth.normalize_frontend_callback(redirect)
    return RedirectResponse(google_auth.build_login_url(target, desktop=desktop))


@api.get("/auth/google/callback")
async def google_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    frontend = google_auth.parse_state(state or "")
    login_url = frontend.replace("/auth/google/callback", "/login")
    if error:
        return RedirectResponse(f"{login_url}?error={google_auth.map_oauth_error(error)}")
    if not code:
        return RedirectResponse(f"{login_url}?error=missing_code")
    try:
        profile = await google_auth.exchange_code(code)
    except ValueError as exc:
        err = str(exc)
        logger.warning("Google callback failed: %s", err)
        mapped = google_auth.map_oauth_error("google_auth_failed", err)
        return RedirectResponse(f"{login_url}?error={mapped}")
    email = profile.get("email")
    if not email:
        return RedirectResponse(f"{login_url}?error=no_email")
    name = profile.get("name") or email.split("@")[0]
    picture = profile.get("picture")
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {
            "name": name or existing.get("name"),
            "picture": picture or existing.get("picture"),
            "auth_provider": "google",
        }})
    else:
        doc = make_user_doc(email, name, picture, "google")
        await db.users.insert_one(doc)
        user_id = doc["user_id"]
    await _get_or_init_license(user_id, email=email)
    exchange = await create_oauth_exchange(user_id)
    finish = f"{EMO_PUBLIC_BACKEND_URL}/api/auth/google/finish?token={exchange}"
    return RedirectResponse(finish)


@api.get("/auth/google/finish")
async def google_finish(token: str = Query(...)):
    """Top-level redirect: pose le cookie session puis renvoie vers le frontend."""
    frontend = os.environ.get("EMO_FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
    login_url = f"{frontend}/login"
    user_id = await consume_oauth_exchange(token)
    if not user_id:
        return RedirectResponse(f"{login_url}?error=missing_token")
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        return RedirectResponse(f"{login_url}?error=google_auth_failed")
    session_token = await create_session(user_id)
    resp = RedirectResponse(f"{frontend}/auth/google/callback?session={session_token}")
    set_session_cookie(resp, session_token)
    return resp


@api.post("/auth/google/exchange")
async def google_exchange(response: Response, token: str = Query(...)):
    user_id = await consume_oauth_exchange(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Jeton Google expiré ou invalide")
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    session_token = await create_session(user_id)
    set_session_cookie(response, session_token)
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "auth_provider": user.get("auth_provider", "google"),
        "session_token": session_token,
    }


@api.post("/auth/google/session")
async def google_session_legacy():
    raise HTTPException(
        status_code=410,
        detail="Utilisez la connexion Google.",
    )


@api.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "user_id": user.user_id, "email": user.email, "name": user.name,
        "picture": user.picture, "auth_provider": user.auth_provider,
        "agent_online": agent_registry.is_online(user.user_id),
    }


@api.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = await get_session_token_from_request(request)
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ============================ LICENSE ============================ #

def _sanitize_error_msg(msg: str) -> str:
    msg = re.sub(r"key=[^&\s'\"]+", "key=***", msg, flags=re.IGNORECASE)
    msg = re.sub(r"sk-[A-Za-z0-9._-]+", "sk-***", msg)
    msg = re.sub(r"AQ\.[A-Za-z0-9._-]+", "AQ.***", msg)
    return msg


def _llm_http_status(exc: Exception) -> Optional[int]:
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


def _http_response_snippet(resp: httpx.Response, max_len: int = 200) -> str:
    try:
        text = resp.text or ""
    except httpx.ResponseNotRead:
        try:
            text = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return ""
    except Exception:
        return ""
    return text[:max_len]


def _friendly_llm_error(exc: Exception) -> str:
    code = _llm_http_status(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            return "Quota API atteint. Réessayez dans quelques minutes."
        if code == 401:
            return "Clé API invalide."
        if code == 402:
            return "Quota gratuit atteint sur ce modèle — essai du suivant…"
        if code == 413:
            return "Requête trop volumineuse."
        if code == 404:
            return "Modèle indisponible."
        if code == 400:
            lower = _http_response_snippet(exc.response, 500).lower()
            if "decommissioned" in lower or "model_decommissioned" in lower:
                return "Modèle vision retiré par Groq — bascule vers un modèle plus récent…"
            if "credit balance" in lower or "too low" in lower or "billing" in lower:
                return "Quota gratuit atteint — essai d'un autre modèle…"
        if code in (400, 402, 403):
            lower = _http_response_snippet(exc.response, 500).lower()
            if "decommissioned" in lower or "model_decommissioned" in lower:
                return "Modèle vision retiré — essai d'un autre modèle…"
            if any(k in lower for k in ("credit balance", "too low", "insufficient", "billing", "quota")):
                return "Quota gratuit atteint — essai d'un autre modèle…"
        snippet = _http_response_snippet(exc.response)
        return _sanitize_error_msg(f"Erreur API ({code})" if not snippet else f"Erreur API ({code})")
    msg = _sanitize_error_msg(str(exc))
    lower = msg.lower()
    if "attempted to access streaming response content" in lower:
        return "Erreur temporaire du service IA."
    if code == 400 and any(k in lower for k in ("credit balance", "too low", "insufficient", "billing")):
        return "Quota gratuit atteint — essai d'un autre modèle…"
    if "429" in msg or "rate limit" in lower or "quota" in lower or "too many requests" in lower:
        return "Quota temporaire atteint — réessayez dans 1 minute."
    if "credit balance" in lower or "too low" in lower:
        return "Quota gratuit atteint — essai d'un autre modèle…"
    return msg or "Erreur IA"


def _retryable_llm_error(exc: Exception) -> bool:
    code = _llm_http_status(exc)
    if code in (429, 402, 413, 404, 403, 503, 500, 502, 504, 408):
        return True
    msg = str(exc).lower()
    if code == 400 and any(k in msg for k in (
        "credit balance", "too low", "insufficient credit",
        "insufficient balance", "billing", "payment required",
        "model", "decommissioned", "not found", "context length",
        "maximum context", "token", "quota", "rate limit",
    )):
        return True
    if code == 401:
        return True
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)):
        return True
    return (
        "429" in msg or "rate limit" in msg or "quota" in msg
        or "too many requests" in msg or "credit balance" in msg
        or "too low" in msg or "insufficient" in msg
        or "not found" in msg or "is not supported" in msg
        or "tool" in msg or "function" in msg
        or "tpm" in msg or "tokens per minute" in msg
        or "model unavailable" in msg or "overloaded" in msg
    )


def _should_fallback_llm(exc: Exception, *, has_output: bool, manual_pick: bool) -> bool:
    if has_output:
        return False
    if _retryable_llm_error(exc):
        return True
    if manual_pick:
        code = _llm_http_status(exc)
        if code in (400, 401, 402, 403, 404, 429, 500, 502, 503):
            return True
    return False


def _block_provider_models(blocked: set[tuple[str, str]], provider: str, candidates: list) -> None:
    for p, m, _ in candidates:
        if p == provider:
            blocked.add((p, m))


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _feedback_month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _feedback_eligible(user_id: str, month: str) -> bool:
    digest = hashlib.sha256(f"{user_id}:{month}".encode()).hexdigest()
    return int(digest[:8], 16) % 100 < 50


async def _feedback_doc(user_id: str, month: str) -> Optional[dict]:
    return await db.feedback_sessions.find_one(
        {"user_id": user_id, "month": month},
        {"_id": 0, "response": 1, "shown_at": 1, "created_at": 1},
    )


async def _get_or_init_license(user_id: str, email: str = None) -> dict:
    doc = await db.licenses.find_one({"user_id": user_id}, {"_id": 0})
    is_admin = bool(email and email.lower() in ADMIN_EMAILS)
    if doc:
        if is_admin and not doc.get("paid"):
            await db.licenses.update_one(
                {"user_id": user_id},
                {"$set": {"paid": True, "status": "active", "paid_at": datetime.now(timezone.utc).isoformat(), "source": "admin_grant"}},
            )
            doc.update({"paid": True, "status": "active", "source": "admin_grant"})
        return doc
    new = {
        "user_id": user_id,
        "status": "active" if is_admin else "free",
        "daily_count": 0,
        "daily_day": _today_key(),
        "paid": is_admin,
        "paid_at": datetime.now(timezone.utc).isoformat() if is_admin else None,
        "stripe_session_id": None,
        "source": "admin_grant" if is_admin else "free",
    }
    await db.licenses.insert_one(new)
    return new


async def _trial_info(lic: dict, is_admin: bool = False) -> dict:
    """Compute access state — tier-aware (free / basic / premium / ultra)."""
    tier = get_user_tier(lic, is_admin=is_admin)
    plan = SUBSCRIPTION_PLANS[tier]
    paid = tier in PAID_TIERS or bool(lic.get("paid") and tier != "free")
    interval = lic.get("interval", "month")
    valid_until_iso = lic.get("valid_until")
    now = datetime.now(timezone.utc)

    sub_expired = False
    if paid and tier != "free" and interval == "month" and valid_until_iso:
        try:
            valid_until = datetime.fromisoformat(valid_until_iso.replace("Z", "+00:00"))
            if valid_until < now:
                sub_expired = True
        except Exception:
            pass

    async def _model_for(t: str) -> tuple[Optional[str], str]:
        try:
            p, _m, label = await resolve_model(t)
            return p, label
        except ValueError:
            return None, "Aucune clé IA — configure OPENAI / ANTHROPIC / DEEPSEEK dans backend/.env"

    if paid and not sub_expired and tier in PAID_TIERS:
        provider, model_label = await _model_for(tier)
        return {
            "status": "active",
            "active": True,
            "tier": tier,
            "tier_name": plan["name"],
            "interval": lic.get("interval", interval),
            "valid_until": valid_until_iso if not lic.get("lifetime") else None,
            "subscription_status": lic.get("subscription_status", "active"),
            "messages_left_today": None,
            "messages_per_day": None,
            "messages_used_today": 0,
            "model_provider": provider,
            "model_label": model_label,
            "lifetime": bool(lic.get("lifetime")),
        }

    if lic.get("source") == "product_key" and lic.get("lifetime"):
        tier = get_user_tier(lic, is_admin=False)
        plan = SUBSCRIPTION_PLANS.get(tier, SUBSCRIPTION_PLANS["ultra"])
        provider, model_label = await _model_for(tier)
        return {
            "status": "active",
            "active": True,
            "tier": tier,
            "tier_name": plan["name"],
            "interval": "lifetime",
            "valid_until": None,
            "subscription_status": "active",
            "messages_left_today": None,
            "messages_per_day": None,
            "messages_used_today": 0,
            "model_provider": provider,
            "model_label": model_label,
            "lifetime": True,
        }

    if is_admin:
        provider, model_label = await _model_for("ultra")
        return {
            "status": "active", "active": True, "tier": "ultra", "tier_name": "Ultra",
            "interval": "lifetime", "valid_until": None,
            "subscription_status": "active",
            "messages_left_today": None, "messages_per_day": None, "messages_used_today": 0,
            "model_provider": provider, "model_label": model_label,
        }

    daily_max = plan.get("messages_per_day") or s("daily_messages") or DAILY_MESSAGES
    today = _today_key()
    used = int(lic.get("daily_count", 0)) if lic.get("daily_day") == today else 0
    left = max(0, daily_max - used)
    active = left > 0
    provider, model_label = await _model_for("free")
    return {
        "status": "expired" if sub_expired else ("free" if active else "rate_limited"),
        "active": active,
        "tier": "free" if not sub_expired else tier,
        "tier_name": plan["name"] if not sub_expired else SUBSCRIPTION_PLANS.get(tier, plan)["name"],
        "interval": interval if paid else None,
        "valid_until": valid_until_iso,
        "subscription_status": lic.get("subscription_status") if paid else None,
        "messages_left_today": left,
        "messages_used_today": used,
        "messages_per_day": daily_max,
        "model_provider": provider,
        "model_label": model_label,
    }


async def assert_license_active(user_id: str, email: str = None):
    is_admin = bool(email and email.lower() in ADMIN_EMAILS)
    lic = await _get_or_init_license(user_id, email=email)
    info = await _trial_info(lic, is_admin=is_admin)
    if not info["active"]:
        tier = info.get("tier", "free")
        if info.get("status") == "expired":
            msg = "Abonnement expiré."
        else:
            daily_max = info.get("messages_per_day") or 15
            msg = f"Quota du jour atteint ({daily_max} msg). Passe Basique (IA gratuites illimitées), Premium (50 €/mois) ou Ultra (80 €/mois)."
        raise HTTPException(
            status_code=402,
            detail={
                "code": "daily_limit_reached" if info.get("status") != "expired" else "subscription_expired",
                "message": msg,
                "info": info,
            },
        )
    return lic, info


@api.get("/license/status")
async def license_status(user: User = Depends(get_current_user)):
    lic = await _get_or_init_license(user.user_id, email=user.email)
    is_admin = user.email.lower() in ADMIN_EMAILS
    info = await _trial_info(lic, is_admin=is_admin)
    info["source"] = lic.get("source", "free")
    info["is_admin"] = is_admin
    info["plans"] = plans_for_api()
    return info


@api.get("/llm/status")
async def llm_status():
    from llm_health import _probe_cache, _PROBE_TTL_SEC
    status = await providers_status()
    live: dict[str, dict] = {}
    now = __import__("time").monotonic()
    for name, configured in status.items():
        row = _probe_cache.get(name)
        if row:
            ok, ts, detail = row
            fresh = (now - ts) <= _PROBE_TTL_SEC
            live[name] = {"ok": ok and fresh, "detail": detail if fresh else "stale"}
        else:
            live[name] = {"ok": configured, "detail": "not probed"}
    status["live"] = live
    status["plans"] = plans_for_api()
    return status


@api.get("/llm/models")
async def llm_models(user: User = Depends(get_current_user)):
    lic = await _get_or_init_license(user.user_id, email=user.email)
    tier = get_user_tier(lic, is_admin=user.email.lower() in ADMIN_EMAILS)
    models = await models_for_tier(tier)
    return {"tier": tier, "models": models, "default": "auto"}


class AdminLlmKeysBody(BaseModel):
    keys: dict[str, Optional[str]] = {}


@api.get("/admin/llm-keys")
async def admin_get_llm_keys(user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin requis")
    doc = await db.app_settings.find_one({"_id": "config"}) or {}
    stored = doc.get("llm_keys") or {}
    out = {}
    for pid, env_key in LLM_ADMIN_KEYS.items():
        val = os.environ.get(env_key, "").strip() or str(stored.get(env_key) or "").strip()
        out[pid] = {
            "env": env_key,
            "configured": bool(val),
            "preview": _mask_secret(val),
        }
    return {"keys": out}


@api.patch("/admin/llm-keys")
async def admin_patch_llm_keys(body: AdminLlmKeysBody, user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin requis")
    doc = await db.app_settings.find_one({"_id": "config"}) or {}
    stored = dict(doc.get("llm_keys") or {})
    for pid, val in (body.keys or {}).items():
        env_key = LLM_ADMIN_KEYS.get(pid)
        if not env_key:
            continue
        if val is None:
            continue
        cleaned = val.strip()
        if cleaned:
            os.environ[env_key] = cleaned
            stored[env_key] = cleaned
        else:
            os.environ.pop(env_key, None)
            stored.pop(env_key, None)
    await db.app_settings.update_one({"_id": "config"}, {"$set": {"llm_keys": stored}}, upsert=True)
    asyncio.create_task(refresh_probe_cache())
    return {"ok": True}


class AdminSettingsBody(BaseModel):
    stripe_payment_link: Optional[str] = None
    stripe_subscription_link: Optional[str] = None
    stripe_basic_link: Optional[str] = None
    stripe_premium_link: Optional[str] = None
    stripe_ultra_link: Optional[str] = None
    license_price_eur: Optional[float] = None
    license_interval: Optional[str] = None
    daily_messages: Optional[int] = None
    subscription_period_days: Optional[int] = None


@api.get("/admin/settings")
async def admin_get_settings(user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin requis")
    await _load_settings()
    return {k: s(k) for k in SETTING_KEYS}


@api.patch("/admin/settings")
async def admin_patch_settings(body: AdminSettingsBody, user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin requis")
    patch = {}
    for field, val in body.model_dump(exclude_unset=True).items():
        if field not in SETTING_KEYS:
            continue
        if val is None:
            continue
        if isinstance(val, str):
            val = val.strip()
        patch[field] = val
    if not patch:
        return {"ok": True, "updated": []}
    await db.app_settings.update_one({"_id": "config"}, {"$set": patch}, upsert=True)
    await _load_settings()
    return {"ok": True, "updated": list(patch.keys()), "settings": {k: s(k) for k in patch}}


@api.get("/subscriptions/plans")
async def subscription_plans():
    return {"plans": plans_for_api()}


class RedeemKeyBody(BaseModel):
    key: str


@api.post("/license/redeem-key")
async def license_redeem_key(body: RedeemKeyBody, user: User = Depends(get_current_user)):
    """Active un abonnement illimité via clé produit (vente)."""
    try:
        result = await redeem_product_key(
            db, raw_key=body.key, user_id=user.user_id, email=user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    lic = await _get_or_init_license(user.user_id, email=user.email)
    is_admin = user.email.lower() in ADMIN_EMAILS
    info = await _trial_info(lic, is_admin=is_admin)
    info["source"] = "product_key"
    return {"ok": True, **result, "license": info}


class GenerateKeysBody(BaseModel):
    tier: str = "ultra"
    count: int = 1
    max_uses: int = 1
    note: str = ""


@api.post("/admin/product-keys/generate")
async def admin_generate_product_keys(body: GenerateKeysBody, user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin uniquement")
    keys = await create_product_keys(
        db,
        tier=body.tier,
        count=body.count,
        max_uses=body.max_uses,
        note=body.note or f"gen by {user.email}",
    )
    return {"ok": True, "keys": keys, "tier": body.tier}


@api.get("/admin/product-keys")
async def admin_list_product_keys(user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin uniquement")
    cursor = db.product_keys.find({}, {"_id": 0, "key_hash": 0}).sort("created_at", -1).limit(100)
    items = await cursor.to_list(100)
    return {"keys": items}


@api.get("/generated-image/{image_id}")
async def get_generated_image(image_id: str, t: str = Query("")):
    """Serve cached generated images (token auth — img tags cannot send Bearer headers)."""
    entry = await _load_generated_image_entry(image_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Image introuvable")
    expected = _image_access_token(entry["user_id"], image_id)
    if not t or t != expected:
        raise HTTPException(status_code=403, detail="Accès refusé")
    try:
        raw = base64.b64decode(entry["b64"])
    except Exception:
        raise HTTPException(status_code=404, detail="Image corrompue")
    if not raw:
        raise HTTPException(status_code=404, detail="Image vide")
    return Response(
        content=raw,
        media_type=entry.get("mime") or "image/png",
        headers={
            "Cache-Control": "private, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


@api.get("/generated-image/{image_id}/b64")
async def get_generated_image_b64(image_id: str, t: str = Query("")):
    """JSON base64 fallback when direct image URL fails (HF multi-worker)."""
    entry = await _load_generated_image_entry(image_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Image introuvable")
    expected = _image_access_token(entry["user_id"], image_id)
    if not t or t != expected:
        raise HTTPException(status_code=403, detail="Accès refusé")
    b64 = entry.get("b64")
    if not b64:
        raise HTTPException(status_code=404, detail="Image vide")
    return JSONResponse(
        {
            "ok": True,
            "image_base64": b64,
            "mime": entry.get("mime") or "image/png",
        },
        headers={"Access-Control-Allow-Origin": "*"},
    )


class FeedbackBody(BaseModel):
    response: str


@api.get("/feedback/eligible")
async def feedback_eligible(user: User = Depends(get_current_user)):
    month = _feedback_month_key()
    in_cohort = _feedback_eligible(user.user_id, month)
    doc = await _feedback_doc(user.user_id, month)
    already_submitted = bool(doc and (doc.get("response") or "").strip())
    already_shown = bool(doc and doc.get("shown_at"))
    return {
        "eligible": in_cohort and not already_shown and not already_submitted,
        "already_submitted": already_submitted,
        "month": month,
    }


@api.post("/feedback/shown")
async def feedback_mark_shown(user: User = Depends(get_current_user)):
    month = _feedback_month_key()
    if not _feedback_eligible(user.user_id, month):
        return {"ok": True}
    now = datetime.now(timezone.utc).isoformat()
    await db.feedback_sessions.update_one(
        {"user_id": user.user_id, "month": month},
        {
            "$setOnInsert": {"created_at": now},
            "$set": {"shown_at": now, "month": month, "user_id": user.user_id},
        },
        upsert=True,
    )
    return {"ok": True}


@api.post("/feedback/skip")
async def feedback_skip(user: User = Depends(get_current_user)):
    month = _feedback_month_key()
    now = datetime.now(timezone.utc).isoformat()
    await db.feedback_sessions.update_one(
        {"user_id": user.user_id, "month": month},
        {
            "$setOnInsert": {"created_at": now},
            "$set": {"shown_at": now, "month": month, "user_id": user.user_id},
        },
        upsert=True,
    )
    return {"ok": True}


@api.post("/feedback")
async def feedback_submit(body: FeedbackBody, user: User = Depends(get_current_user)):
    month = _feedback_month_key()
    text = (body.response or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Réponse vide")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Réponse trop longue (5000 car. max)")
    now = datetime.now(timezone.utc).isoformat()
    await db.feedback_sessions.update_one(
        {"user_id": user.user_id, "month": month},
        {
            "$set": {
                "response": text,
                "created_at": now,
                "shown_at": now,
                "month": month,
                "user_id": user.user_id,
            },
        },
        upsert=True,
    )
    return {"ok": True}


@api.get("/admin/feedback-sessions")
async def admin_feedback_sessions(user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin requis")
    cursor = db.feedback_sessions.find(
        {},
        {"_id": 0, "month": 1, "response": 1, "shown_at": 1, "created_at": 1},
    )
    docs = await cursor.to_list(5000)
    by_month: dict[str, dict] = {}
    for doc in docs:
        month = doc.get("month") or "unknown"
        bucket = by_month.setdefault(
            month,
            {
                "month": month,
                "total_shown": 0,
                "total_responses": 0,
                "sample_responses": [],
                "latest_at": None,
            },
        )
        if doc.get("shown_at"):
            bucket["total_shown"] += 1
        resp = (doc.get("response") or "").strip()
        if resp:
            bucket["total_responses"] += 1
            if len(bucket["sample_responses"]) < 3:
                bucket["sample_responses"].append(resp)
        ts = doc.get("created_at") or doc.get("shown_at")
        if ts and (not bucket["latest_at"] or ts > bucket["latest_at"]):
            bucket["latest_at"] = ts
    sessions = sorted(by_month.values(), key=lambda row: row["month"], reverse=True)
    for row in sessions:
        n = row["total_responses"]
        if n == 0:
            row["summary"] = "Aucune réponse ce mois."
        elif n == 1:
            row["summary"] = "1 retour utilisateur."
        else:
            row["summary"] = f"{n} retours utilisateurs."
    return {"sessions": sessions}


class CheckoutBody(BaseModel):
    origin_url: str
    tier: Optional[str] = "basic"  # basic | premium | ultra


@api.post("/license/checkout")
async def license_checkout(body: CheckoutBody, request: Request, user: User = Depends(get_current_user)):
    tier = (body.tier or "basic").lower()
    if tier not in ("basic", "premium", "ultra"):
        raise HTTPException(status_code=400, detail="Tier invalide (basic, premium ou ultra)")

    lic = await _get_or_init_license(user.user_id, email=user.email)
    is_admin = user.email.lower() in ADMIN_EMAILS
    info = await _trial_info(lic, is_admin=is_admin)
    current_tier = get_user_tier(lic, is_admin=is_admin)
    if TIER_RANK.get(current_tier, 0) >= TIER_RANK.get(tier, 0) and info.get("active") and current_tier != "free":
        return {"already_paid": True, "tier": current_tier, "subscription_status": lic.get("subscription_status", "active")}

    plan = SUBSCRIPTION_PLANS[tier]
    price = plan["price_eur"]
    link = stripe_link_for_tier(tier)
    ref = f"{user.user_id}__{tier}"

    if link:
        sep = "&" if "?" in link else "?"
        url = f"{link}{sep}prefilled_email={user.email}&client_reference_id={ref}"
        await db.payment_transactions.insert_one({
            "session_id": f"link_{uuid.uuid4().hex}",
            "user_id": user.user_id,
            "email": user.email,
            "amount": price,
            "currency": LICENSE_CURRENCY,
            "payment_status": "pending",
            "status": "redirected_to_payment_link",
            "method": "subscription",
            "product": f"emo_{tier}",
            "tier": tier,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"url": url, "method": "subscription", "product": f"emo_{tier}", "tier": tier, "price_eur": price}

    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe non configuré")
    host = str(request.base_url).rstrip("/")
    stripe = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host}/api/webhook/stripe")
    origin = body.origin_url.rstrip("/")
    req = CheckoutSessionRequest(
        amount=price, currency=LICENSE_CURRENCY,
        success_url=f"{origin}/chat?stripe_session_id={{CHECKOUT_SESSION_ID}}&tier={tier}",
        cancel_url=f"{origin}/chat?stripe_canceled=1",
        metadata={"user_id": user.user_id, "email": user.email, "product": f"emo_{tier}", "tier": tier},
        mode="subscription",
    )
    session: CheckoutSessionResponse = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user.user_id, "email": user.email,
        "amount": price, "currency": LICENSE_CURRENCY,
        "payment_status": "pending", "status": "initiated",
        "metadata": {"product": f"emo_{tier}", "tier": tier},
        "tier": tier,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id, "tier": tier, "price_eur": price}


@api.post("/license/claim-payment")
async def claim_payment(user: User = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one(
        {"user_id": user.user_id, "payment_status": "paid"},
        {"_id": 0},
    )
    if not txn:
        return {"paid": False, "message": "Paiement en attente."}
    tier = txn.get("tier") or "basic"
    now = datetime.now(timezone.utc)
    await db.licenses.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "paid": True, "status": "active", "tier": tier,
            "paid_at": now.isoformat(),
            "interval": "month",
            "valid_until": (now + timedelta(days=SUBSCRIPTION_PERIOD_DAYS)).isoformat(),
        }},
    )
    return {"paid": True, "tier": tier}


@api.get("/license/checkout/status/{session_id}")
async def license_checkout_status(session_id: str, request: Request, user: User = Depends(get_current_user)):
    """Polled by frontend after Stripe redirect."""
    txn = await db.payment_transactions.find_one(
        {"session_id": session_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    # If already processed, short-circuit
    if txn.get("payment_status") == "paid":
        return {"payment_status": "paid", "status": "complete", "already_processed": True}

    host = str(request.base_url).rstrip("/")
    stripe = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host}/api/webhook/stripe")
    status = await stripe.get_checkout_status(session_id)

    # Update transaction
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {
            "status": status.status,
            "payment_status": status.payment_status,
            "amount_total": status.amount_total,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    # Activate license if paid (only once)
    if status.payment_status == "paid":
        lic = await db.licenses.find_one({"user_id": user.user_id}, {"_id": 0})
        if lic and not lic.get("paid"):
            await db.licenses.update_one(
                {"user_id": user.user_id},
                {"$set": {
                    "paid": True,
                    "status": "active",
                    "paid_at": datetime.now(timezone.utc).isoformat(),
                    "stripe_session_id": session_id,
                }},
            )

    return {
        "payment_status": status.payment_status,
        "status": status.status,
        "amount_total": status.amount_total,
        "currency": status.currency,
    }


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe events.

    Supports:
    - One-time payment: checkout.session.completed with mode=payment
    - Subscription: checkout.session.completed with mode=subscription (first paid invoice)
    - Subscription renewal: invoice.paid
    - Subscription cancellation: customer.subscription.deleted
    - Payment failure: invoice.payment_failed
    """
    raw = await request.body()
    sig = request.headers.get("Stripe-Signature", "")

    # Try emergent stripe helper first (works for API checkout sessions)
    evt = None
    if STRIPE_API_KEY:
        try:
            host = str(request.base_url).rstrip("/")
            stripe = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host}/api/webhook/stripe")
            evt = await stripe.handle_webhook(raw, sig)
        except Exception as e:
            logger.info("Stripe webhook (helper) parse failed, fallback to raw: %s", e)

    try:
        payload = json.loads(raw.decode())
    except Exception:
        payload = {}

    event_type = payload.get("type", "")
    obj = (payload.get("data") or {}).get("object") or {}

    # --- 1. Activation event (first checkout / one-time payment) ---
    is_activation = (
        event_type == "checkout.session.completed"
        or event_type == "payment_intent.succeeded"
        or obj.get("payment_status") == "paid"
    )

    if is_activation and event_type != "invoice.paid":
        raw_ref = (
            obj.get("client_reference_id")
            or (obj.get("metadata") or {}).get("user_id")
            or (evt.metadata if evt and evt.metadata else {}).get("user_id")
        )
        user_id, tier = parse_client_reference(raw_ref)
        tier = (obj.get("metadata") or {}).get("tier") or tier or "basic"
        if tier not in SUBSCRIPTION_PLANS:
            tier = "basic"
        customer_email = (
            obj.get("customer_email")
            or (obj.get("customer_details") or {}).get("email")
        )
        if not user_id and customer_email:
            u = await db.users.find_one({"email": customer_email}, {"_id": 0, "user_id": 1})
            user_id = u["user_id"] if u else None

        if user_id:
            session_id = obj.get("id") or (evt.session_id if evt else None) or f"link_{uuid.uuid4().hex}"
            mode = obj.get("mode", "payment")  # "subscription" if it's a sub
            subscription_id = obj.get("subscription")  # Stripe sub ID for renewals
            stripe_customer_id = obj.get("customer")
            interval = "month" if (mode == "subscription" or subscription_id) else "lifetime"
            now = datetime.now(timezone.utc)
            valid_until = (now + timedelta(days=SUBSCRIPTION_PERIOD_DAYS)).isoformat() if interval == "month" else None

            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "user_id": user_id, "session_id": session_id,
                    "payment_status": "paid", "status": "complete",
                    "email": customer_email,
                    "subscription_id": subscription_id,
                    "stripe_customer_id": stripe_customer_id,
                    "updated_at": now.isoformat(),
                }},
                upsert=True,
            )
            license_set = {
                "paid": True, "status": "active",
                "tier": tier,
                "interval": interval,
                "subscription_status": "active",
                "paid_at": now.isoformat(),
                "stripe_session_id": session_id,
                "source": "stripe",
            }
            if subscription_id:
                license_set["stripe_subscription_id"] = subscription_id
            if stripe_customer_id:
                license_set["stripe_customer_id"] = stripe_customer_id
            if valid_until:
                license_set["valid_until"] = valid_until

            await db.licenses.update_one(
                {"user_id": user_id},
                {"$set": license_set, "$setOnInsert": {
                    "user_id": user_id, "daily_count": 0, "daily_day": _today_key(),
                }},
                upsert=True,
            )
            logger.info("License activated for user %s via Stripe (tier=%s, interval=%s)", user_id, tier, interval)
        else:
            logger.warning("Stripe activation event but no user_id/email match. Event id=%s email=%s", obj.get("id"), customer_email)

    # --- 2. Subscription renewal (invoice.paid for recurring) ---
    elif event_type == "invoice.paid":
        subscription_id = obj.get("subscription")
        period_end = obj.get("period_end") or obj.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
        if subscription_id:
            lic = await db.licenses.find_one({"stripe_subscription_id": subscription_id}, {"_id": 0})
            if lic:
                from datetime import datetime as _dt
                if period_end:
                    # period_end is a Unix timestamp
                    valid_until = _dt.fromtimestamp(int(period_end), tz=timezone.utc).isoformat()
                else:
                    valid_until = (datetime.now(timezone.utc) + timedelta(days=SUBSCRIPTION_PERIOD_DAYS)).isoformat()
                await db.licenses.update_one(
                    {"user_id": lic["user_id"]},
                    {"$set": {
                        "paid": True, "status": "active",
                        "subscription_status": "active",
                        "valid_until": valid_until,
                        "last_invoice_paid_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                logger.info("Subscription renewed for user %s, valid_until=%s", lic["user_id"], valid_until)
            else:
                logger.warning("invoice.paid received but no matching license for subscription %s", subscription_id)

    # --- 3. Subscription cancelled (still active until period end) ---
    elif event_type == "customer.subscription.deleted":
        subscription_id = obj.get("id")
        lic = await db.licenses.find_one({"stripe_subscription_id": subscription_id}, {"_id": 0})
        if lic:
            await db.licenses.update_one(
                {"user_id": lic["user_id"]},
                {"$set": {
                    "subscription_status": "cancelled",
                    "cancelled_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            logger.info("Subscription cancelled for user %s (still active until valid_until)", lic["user_id"])

    # --- 4. Payment failed (mark past_due, keep access until valid_until) ---
    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            lic = await db.licenses.find_one({"stripe_subscription_id": subscription_id}, {"_id": 0})
            if lic:
                await db.licenses.update_one(
                    {"user_id": lic["user_id"]},
                    {"$set": {
                        "subscription_status": "past_due",
                        "last_payment_failed_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                logger.warning("Subscription past_due for user %s", lic["user_id"])

    return {"ok": True}


# ============================ PROFILE / PREFERENCES ============================ #


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    custom_prompt_addon: Optional[str] = None
    theme_mode: Optional[str] = None  # "dark" | "light" | "system"


@api.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "password_hash": 0})
    lic = await _get_or_init_license(user.user_id, email=user.email)
    is_admin = user.email.lower() in ADMIN_EMAILS
    info = await _trial_info(lic, is_admin=is_admin)
    info["source"] = lic.get("source", "free")
    info["is_admin"] = is_admin
    return {
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "name": user_doc.get("name"),
            "picture": user_doc.get("picture"),
            "auth_provider": user.auth_provider,
            "created_at": user_doc.get("created_at"),
        },
        "preferences": {
            "custom_prompt_addon": user_doc.get("custom_prompt_addon", ""),
            "theme_mode": user_doc.get("theme_mode", "dark"),
        },
        "license": info,
        "plans": plans_for_api(),
    }


@api.patch("/profile")
async def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user)):
    update = {}
    if body.name is not None:
        update["name"] = body.name.strip()[:80]
    if body.custom_prompt_addon is not None:
        update["custom_prompt_addon"] = body.custom_prompt_addon.strip()[:4000]
    if body.theme_mode is not None and body.theme_mode in {"dark", "light", "system"}:
        update["theme_mode"] = body.theme_mode
    if update:
        await db.users.update_one({"user_id": user.user_id}, {"$set": update})
    return {"ok": True, "updated": list(update.keys())}


@api.post("/profile/reset-license")
async def reset_license(user: User = Depends(get_current_user)):
    """Admin only: revoke own paid license (for testing or refund)."""
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Réservé aux admins")
    await db.licenses.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "paid": False,
            "status": "trial",
            "paid_at": None,
            "stripe_session_id": None,
            "trial_started_at": datetime.now(timezone.utc).isoformat(),
            "trial_message_count": 0,
            "source": "reset",
        }},
    )
    return {"ok": True}


@api.delete("/profile")
async def delete_account(user: User = Depends(get_current_user)):
    """Permanently delete user account + all data."""
    uid = user.user_id
    await db.users.delete_one({"user_id": uid})
    await db.user_sessions.delete_many({"user_id": uid})
    await db.conversations.delete_many({"user_id": uid})
    await db.messages.delete_many({"user_id": uid})
    await db.memories.delete_many({"user_id": uid})
    await db.licenses.delete_many({"user_id": uid})
    await db.agent_tokens.delete_many({"user_id": uid})
    await db.connected_accounts.delete_many({"user_id": uid})
    return {"ok": True}


# ============================ CONNECTED ACCOUNTS ============================ #

@api.get("/connections")
async def list_connections(user: User = Depends(get_current_user)):
    """List linked OAuth accounts for the current user (no tokens exposed)."""
    accounts = await conn_accounts.list_public_accounts(db, user.user_id)
    return {"accounts": accounts}


@api.get("/oauth/{provider}/start")
async def oauth_connect_start(
    provider: str,
    request: Request,
    return_url: str = Query(default=""),
    session: str = Query(default=""),
):
    provider = provider.lower().strip()
    if provider not in conn_accounts.PROVIDER_IDS:
        raise HTTPException(status_code=404, detail="Provider inconnu")
    if not conn_accounts.is_provider_configured(provider):
        raise HTTPException(
            status_code=503,
            detail=f"{conn_accounts.PROVIDERS[provider]['label']} OAuth non configuré sur le serveur",
        )
    token = await get_session_token_from_request(request) or (session.strip() if session else None)
    user = await resolve_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    target = conn_accounts.normalize_return_url(return_url or request.headers.get("referer", ""))
    url = conn_accounts.build_authorize_url(provider, user.user_id, target)
    return RedirectResponse(url)


@api.get("/oauth/{provider}/callback")
async def oauth_connect_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    provider = provider.lower().strip()
    if provider not in conn_accounts.PROVIDER_IDS:
        raise HTTPException(status_code=404, detail="Provider inconnu")
    user_id, return_url = conn_accounts.decode_state(state or "")
    sep = "&" if "?" in return_url else "?"
    if error:
        return RedirectResponse(f"{return_url}{sep}provider={provider}&status=error&error={error}")
    if not user_id or not code:
        return RedirectResponse(f"{return_url}{sep}provider={provider}&status=error&error=missing_code")
    if not conn_accounts.is_provider_configured(provider):
        return RedirectResponse(f"{return_url}{sep}provider={provider}&status=error&error=not_configured")
    try:
        token_data = await conn_accounts.exchange_code(provider, code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("missing_access_token")
        profile = await conn_accounts.fetch_profile(provider, access_token)
        await conn_accounts.store_connection(db, user_id, provider, token_data, profile)
    except ValueError as exc:
        logger.warning("OAuth connect %s failed: %s", provider, exc)
        return RedirectResponse(f"{return_url}{sep}provider={provider}&status=error&error=exchange_failed")
    return RedirectResponse(f"{return_url}{sep}provider={provider}&status=ok")


@api.delete("/connections/{provider}")
async def disconnect_connection(provider: str, user: User = Depends(get_current_user)):
    provider = provider.lower().strip()
    if provider not in conn_accounts.PROVIDER_IDS:
        raise HTTPException(status_code=404, detail="Provider inconnu")
    removed = await conn_accounts.disconnect_account(db, user.user_id, provider)
    if not removed:
        raise HTTPException(status_code=404, detail="Compte non connecté")
    return {"ok": True, "provider": provider}


@api.get("/admin/connected-accounts")
async def admin_connected_accounts(user: User = Depends(get_current_user)):
    """Admin: view own linked accounts (tokens never exposed)."""
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Réservé aux admins")
    accounts = await conn_accounts.list_public_accounts(db, user.user_id)
    return {"accounts": accounts, "note": "Google token stored for future Gmail/Drive tools"}


# ---- Admin only: export the whole project as a tarball ---- #

EXPORT_EXCLUDES = {
    "node_modules", ".git", "__pycache__", ".next", ".cache", "build", "dist",
    ".venv", "venv", ".env", "agent_binaries",
    ".pytest_cache", ".mypy_cache", ".DS_Store",
}


def _should_skip(name: str) -> bool:
    return name in EXPORT_EXCLUDES or name.endswith(".pyc") or name.endswith(".log")


def _sanitize_env(text: str) -> str:
    out = []
    for line in text.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            out.append(f"{key}=CHANGE_ME")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


@api.get("/admin/project-export", include_in_schema=False)
async def export_project(user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Réservé aux admins")
    import io
    import tarfile

    root = ROOT_DIR.parent
    include = ["backend", "frontend", "agent", "agent-go", "memory", "SELF_HOSTING.md", "auth_testing.md"]

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for top in include:
            top_path = root / top
            if not top_path.exists():
                continue
            if top_path.is_file():
                tf.add(str(top_path), arcname=f"emo/{top}")
                continue
            for path in top_path.rglob("*"):
                if any(_should_skip(p) for p in path.parts):
                    continue
                if path.is_dir() or path.is_symlink():
                    continue
                rel = path.relative_to(root)
                tf.add(str(path), arcname=f"emo/{rel}")

        def add_str(arcname: str, content: str):
            data = content.encode()
            ti = tarfile.TarInfo(name=arcname)
            ti.size = len(data)
            ti.mode = 0o644
            tf.addfile(ti, io.BytesIO(data))

        for env_name in ("backend/.env", "frontend/.env"):
            env_path = root / env_name
            if env_path.exists():
                add_str(f"emo/{env_name}.example", _sanitize_env(env_path.read_text()))

    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/gzip",
        headers={"Content-Disposition": 'attachment; filename="emo-source.tar.gz"'},
    )


class EmoRestoreBody(BaseModel):
    version_id: str


@api.get("/admin/emo-identity")
async def admin_get_emo_identity(user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Réservé aux admins")
    data = await emo_read_self(db)
    if not data.get("ok"):
        raise HTTPException(status_code=500, detail=data.get("error", "Erreur"))
    return data


@api.get("/admin/emo-identity/versions")
async def admin_list_emo_versions(user: User = Depends(get_current_user), limit: int = 20):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Réservé aux admins")
    return await emo_list_self_saves(db, limit=limit)


@api.post("/admin/emo-identity/restore")
async def admin_restore_emo_identity(body: EmoRestoreBody, user: User = Depends(get_current_user)):
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Réservé aux admins")
    result = await emo_restore_self(db, user.user_id, body.version_id.strip())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Restauration échouée"))
    return result


# ============================ CONVERSATIONS ============================ #


@api.get("/conversations")
async def list_conversations(user: User = Depends(get_current_user)):
    docs = await db.conversations.find({"user_id": user.user_id}, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return docs


@api.post("/conversations")
async def create_conversation(body: CreateConversationBody, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "conversation_id": f"conv_{uuid.uuid4().hex[:12]}",
        "user_id": user.user_id,
        "title": body.title or "Nouvelle conversation",
        "mode": body.mode or "normal",
        "created_at": now, "updated_at": now,
    }
    await db.conversations.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, body: RenameConversationBody, user: User = Depends(get_current_user)):
    res = await db.conversations.update_one(
        {"conversation_id": conversation_id, "user_id": user.user_id},
        {"$set": {"title": body.title, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"ok": True}


@api.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: User = Depends(get_current_user)):
    res = await db.conversations.delete_one({"conversation_id": conversation_id, "user_id": user.user_id})
    await db.messages.delete_many({"conversation_id": conversation_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"ok": True}


@api.get("/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: str, user: User = Depends(get_current_user)):
    conv = await db.conversations.find_one(
        {"conversation_id": conversation_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    msgs = await db.messages.find(
        {"conversation_id": conversation_id, "user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(2000)
    return msgs


# ============================ MEMORY ============================ #

@api.get("/memories")
async def list_memories(user: User = Depends(get_current_user)):
    docs = await db.memories.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api.post("/memories")
async def create_memory(body: MemoryBody, user: User = Depends(get_current_user)):
    doc = {
        "memory_id": f"mem_{uuid.uuid4().hex[:12]}",
        "user_id": user.user_id,
        "content": body.content.strip(),
        "source": "manual",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.memories.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, user: User = Depends(get_current_user)):
    res = await db.memories.delete_one({"memory_id": memory_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Mémoire introuvable")
    return {"ok": True}


async def _load_user_memories(user_id: str, limit: int = 50) -> list[str]:
    docs = await db.memories.find({"user_id": user_id}, {"_id": 0, "content": 1}).sort("created_at", -1).to_list(limit)
    return [d["content"] for d in docs if d.get("content")]


async def _extract_and_store_memories(user_id: str, user_text: str, emo_text: str):
    """Background task: extract durable facts from a conversation turn."""
    try:
        extractor = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"mem_{uuid.uuid4().hex}",
            system_message=MEMORY_EXTRACTION_PROMPT,
            provider="groq" if os.environ.get("GROQ_API_KEY") else "anthropic",
            model="llama-3.3-70b-versatile" if os.environ.get("GROQ_API_KEY") else "claude-sonnet-4-20250514",
        ).with_model("groq" if os.environ.get("GROQ_API_KEY") else "anthropic",
                     "llama-3.3-70b-versatile" if os.environ.get("GROQ_API_KEY") else "claude-sonnet-4-20250514")
        prompt = f"--- Hugo a dit ---\n{user_text}\n\n--- Émo a répondu ---\n{emo_text}"
        resp = await extractor.send_message(UserMessage(text=prompt))
        raw = resp.strip() if isinstance(resp, str) else getattr(resp, "content", "") or ""
        # Find first JSON array in response
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return
        facts = json.loads(match.group(0))
        if not isinstance(facts, list):
            return
        existing = set(await _load_user_memories(user_id, limit=500))
        for fact in facts[:5]:
            if not isinstance(fact, str) or not fact.strip():
                continue
            fact_clean = fact.strip()[:500]
            if fact_clean in existing:
                continue
            await db.memories.insert_one({
                "memory_id": f"mem_{uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "content": fact_clean,
                "source": "auto",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            existing.add(fact_clean)
    except Exception as e:
        logger.warning("Memory extraction failed: %s", e)


# ============================ AGENT TOKEN ============================ #

@api.get("/agent/token")
async def get_agent_token(user: User = Depends(get_current_user)):
    """Return or create the user's persistent agent token."""
    doc = await db.agent_tokens.find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        token = f"agent_{uuid.uuid4().hex}"
        doc = {
            "agent_token": token,
            "user_id": user.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.agent_tokens.insert_one(doc)
        doc.pop("_id", None)
    else:
        # Garantir un token unique en base
        dup = await db.agent_tokens.count_documents({
            "agent_token": doc["agent_token"],
            "user_id": {"$ne": user.user_id},
        })
        if dup:
            token = f"agent_{uuid.uuid4().hex}"
            await db.agent_tokens.update_one(
                {"user_id": user.user_id},
                {"$set": {"agent_token": token, "created_at": datetime.now(timezone.utc).isoformat()}},
            )
            doc["agent_token"] = token
    return {"agent_token": doc["agent_token"], "online": agent_registry.is_online(user.user_id)}


@api.post("/agent/token/rotate")
async def rotate_agent_token(user: User = Depends(get_current_user)):
    token = f"agent_{uuid.uuid4().hex}"
    await db.agent_tokens.update_one(
        {"user_id": user.user_id},
        {"$set": {"agent_token": token, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"agent_token": token}


@api.get("/agent/status")
async def agent_status(user: User = Depends(get_current_user)):
    ctx = agent_registry.get_context(user.user_id)
    return {
        "online": agent_registry.is_online(user.user_id),
        "context": ctx if ctx else None,
    }


# Agent long-polling endpoints
async def _resolve_agent_user(token: str) -> Optional[str]:
    if not token:
        return None
    doc = await db.agent_tokens.find_one({"agent_token": token}, {"_id": 0, "user_id": 1})
    return doc["user_id"] if doc else None


@api.get("/agent/poll")
async def agent_poll(token: str = Query(...)):
    user_id = await _resolve_agent_user(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token agent invalide")
    req = await agent_registry.poll(user_id, timeout=25.0)
    if req is None:
        return {"empty": True}
    return {"empty": False, "request": req}


@api.post("/agent/result")
async def agent_result(token: str = Query(...), payload: dict = Body(...)):
    user_id = await _resolve_agent_user(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token agent invalide")
    agent_registry.heartbeat(user_id)
    request_id = payload.get("id")
    result = payload.get("result") or {}
    if request_id:
        agent_registry.resolve(request_id, {"result": result})
    return {"ok": True}


@api.post("/agent/heartbeat")
async def agent_heartbeat(token: str = Query(...), body: Optional[dict] = Body(default=None)):
    user_id = await _resolve_agent_user(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token agent invalide")
    agent_registry.heartbeat(user_id, context=body)
    return {"ok": True}


# UI -> Agent proxy endpoints (used by the file tree / editor in the right panel)
class FileWriteBody(BaseModel):
    path: str
    content: str


@api.get("/agent/fs/list")
async def agent_fs_list(path: str = "~", user: User = Depends(get_current_user)):
    result = await execute_tool(user.user_id, "list_dir", {"path": path})
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur agent"))
    return result


@api.get("/agent/fs/read")
async def agent_fs_read(path: str, user: User = Depends(get_current_user)):
    result = await execute_tool(user.user_id, "read_file", {"path": path})
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur agent"))
    return result


@api.post("/agent/fs/write")
async def agent_fs_write(body: FileWriteBody, user: User = Depends(get_current_user)):
    result = await execute_tool(user.user_id, "write_file", {"path": body.path, "content": body.content})
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur agent"))
    return result


# ============================ INTERACTIVE BROWSER (Playwright) ============================ #

class BrowserOpenBody(BaseModel):
    url: str
    session_id: str = "default"
    fast: bool = True


class BrowserSessionBody(BaseModel):
    session_id: str = "default"
    fast: bool = True


class BrowserClickBody(BaseModel):
    session_id: str = "default"
    ref: Optional[int] = None
    selector: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    fast: bool = True


class BrowserTypeBody(BaseModel):
    session_id: str = "default"
    ref: Optional[int] = None
    selector: Optional[str] = None
    text: str
    clear: bool = False
    press_enter: bool = False
    fast: bool = True


class BrowserFillBody(BaseModel):
    session_id: str = "default"
    ref: Optional[int] = None
    selector: Optional[str] = None
    text: str
    press_enter: bool = False
    fast: bool = True


class BrowserScrollBody(BaseModel):
    session_id: str = "default"
    direction: str = "down"
    amount: int = 600
    fast: bool = True


class BrowserKeyBody(BaseModel):
    session_id: str = "default"
    key: Optional[str] = None
    text: Optional[str] = None
    fast: bool = True
    snapshot: bool = True


def _browser_available() -> bool:
    from browser_control import PLAYWRIGHT_AVAILABLE
    if os.environ.get("EMO_BROWSER_HARD_DISABLE", "").lower() in ("1", "true", "yes"):
        return False
    if PLAYWRIGHT_AVAILABLE:
        return True
    return os.environ.get("EMO_BROWSER_ENABLED", "true").lower() not in ("0", "false", "no")


@api.get("/browser/status")
async def browser_status():
    from browser_control import PLAYWRIGHT_AVAILABLE
    hard_off = os.environ.get("EMO_BROWSER_HARD_DISABLE", "").lower() in ("1", "true", "yes")
    legacy_flag = os.environ.get("EMO_BROWSER_ENABLED", "true").lower() not in ("0", "false", "no")
    available = PLAYWRIGHT_AVAILABLE and not hard_off
    return {
        "available": available,
        "playwright": PLAYWRIGHT_AVAILABLE,
        "enabled": legacy_flag,
    }


@api.post("/browser/open")
async def user_browser_open(body: BrowserOpenBody, user: User = Depends(get_current_user)):
    if not _browser_available():
        raise HTTPException(status_code=503, detail="Navigateur interactif indisponible sur ce serveur.")
    result = await do_browser_open(user.user_id, body.url.strip(), body.session_id or "default", fast=body.fast)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Navigation échouée"))
    return result


@api.post("/browser/snapshot")
async def user_browser_snapshot(body: BrowserSessionBody, user: User = Depends(get_current_user)):
    if not _browser_available():
        raise HTTPException(status_code=503, detail="Navigateur interactif indisponible.")
    result = await do_browser_snapshot(user.user_id, body.session_id or "default", fast=body.fast)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Snapshot échoué"))
    return result


@api.post("/browser/click")
async def user_browser_click(body: BrowserClickBody, user: User = Depends(get_current_user)):
    if not _browser_available():
        raise HTTPException(status_code=503, detail="Navigateur interactif indisponible.")
    result = await do_browser_click(
        user.user_id, body.session_id or "default",
        ref=body.ref, selector=body.selector, x=body.x, y=body.y,
        fast=body.fast,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Clic échoué"))
    return result


@api.post("/browser/type")
async def user_browser_type(body: BrowserTypeBody, user: User = Depends(get_current_user)):
    if not _browser_available():
        raise HTTPException(status_code=503, detail="Navigateur interactif indisponible.")
    result = await do_browser_type(
        user.user_id,
        body.text,
        body.session_id or "default",
        ref=body.ref,
        selector=body.selector,
        clear=body.clear,
        press_enter=body.press_enter,
        fast=body.fast,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Saisie échouée"))
    return result


@api.post("/browser/fill")
async def user_browser_fill(body: BrowserFillBody, user: User = Depends(get_current_user)):
    if not _browser_available():
        raise HTTPException(status_code=503, detail="Navigateur interactif indisponible.")
    result = await do_browser_fill(
        user.user_id,
        body.text,
        body.session_id or "default",
        ref=body.ref,
        selector=body.selector,
        press_enter=body.press_enter,
        fast=body.fast,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Remplissage échoué"))
    return result


@api.post("/browser/scroll")
async def user_browser_scroll(body: BrowserScrollBody, user: User = Depends(get_current_user)):
    if not _browser_available():
        raise HTTPException(status_code=503, detail="Navigateur interactif indisponible.")
    result = await do_browser_scroll(
        user.user_id, body.direction, body.amount, body.session_id or "default",
        fast=body.fast,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Scroll échoué"))
    return result


@api.post("/browser/key")
async def user_browser_key(body: BrowserKeyBody, user: User = Depends(get_current_user)):
    if not _browser_available():
        raise HTTPException(status_code=503, detail="Navigateur interactif indisponible.")
    if not body.key and not body.text:
        raise HTTPException(status_code=400, detail="Indique key ou text.")
    result = await do_browser_keyboard(
        user.user_id,
        body.session_id or "default",
        key=body.key,
        text=body.text,
        fast=body.fast,
        snapshot=body.snapshot,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Saisie clavier échouée"))
    return result


# ============================ TOOL EXECUTION ============================ #

LOCAL_AGENT_TOOLS = {
    "exec_shell", "read_file", "write_file", "list_dir",
    "grep", "edit_file", "delete_path", "move_path", "find_files",
    "codebase_search", "append_file", "create_dir", "copy_path", "file_info",
    "get_env", "system_info", "git_status", "git_diff", "apply_patch", "download_url",
    "run_terminal_cmd", "bash", "file_search", "delete_file", "create_file",
    "grep_search", "run_terminal_command",
}

TOOL_ALIASES = {
    "run_terminal_cmd": "exec_shell",
    "run_terminal_command": "exec_shell",
    "bash": "exec_shell",
    "file_search": "find_files",
    "delete_file": "delete_path",
    "create_file": "write_file",
    "grep_search": "grep",
    "str_replace_based_edit_tool": "edit_file",
    "str_replace_editor": "edit_file",
}


async def execute_tool(
    user_id: str,
    tool_name: str,
    args: dict,
    *,
    is_owner: bool = False,
    allow_local_agent: bool = True,
) -> dict:
    """Dispatch a Claude tool call to the user's local agent OR to a backend web tool."""
    tool_name = TOOL_ALIASES.get(tool_name, tool_name)
    # Web tools run on the backend directly (no local agent required)
    if tool_name == "web_search":
        return await do_web_search(
            args.get("query", ""),
            int(args.get("limit", 10) or 10),
            str(args.get("focus") or "general"),
            args.get("queries"),
        )
    if tool_name == "web_fetch":
        return await do_web_fetch(args.get("url", ""), int(args.get("max_chars", 12000) or 12000))
    if tool_name == "browser_visit":
        return await do_browser_visit(args.get("url", ""), int(args.get("max_chars", 10000) or 10000))
    if tool_name == "web_fetch_json":
        return await do_web_fetch_json(args.get("url", ""), int(args.get("max_chars", 8000) or 8000))
    if tool_name == "get_datetime":
        return await do_get_datetime(str(args.get("timezone") or "UTC"))
    if tool_name == "github_search":
        gh_token = await conn_accounts.get_account_token(db, user_id, "github")
        return await do_github_search(
            args.get("query", ""),
            int(args.get("limit", 8) or 8),
            access_token=gh_token,
        )
    if tool_name == "github_api":
        gh_token = await conn_accounts.get_account_token(db, user_id, "github")
        if not gh_token:
            return {
                "ok": False,
                "error": "GitHub non connecté. L'utilisateur doit lier son compte GitHub dans Paramètres → Comptes connectés.",
            }
        return await do_github_api(
            gh_token,
            str(args.get("method") or "GET"),
            str(args.get("path") or ""),
            params=args.get("params"),
            json_body=args.get("json"),
        )
    if tool_name == "stackoverflow_search":
        return await do_stackoverflow_search(args.get("query", ""), int(args.get("limit", 8) or 8))
    if tool_name == "calculate":
        return do_calculate(args.get("expression", ""))
    if tool_name == "generate_image":
        seed_raw = args.get("seed")
        seed = int(seed_raw) if seed_raw is not None and str(seed_raw).strip().isdigit() else None
        return await do_generate_image(
            str(args.get("prompt", "")),
            str(args.get("size") or "1024x1024"),
            seed=seed,
        )

    sid = str(args.get("session_id") or "default")
    if tool_name == "browser_open":
        return await do_browser_open(user_id, str(args.get("url", "")), sid)
    if tool_name == "browser_snapshot":
        return await do_browser_snapshot(user_id, sid)
    if tool_name == "browser_click":
        return await do_browser_click(
            user_id, sid,
            ref=args.get("ref"),
            selector=args.get("selector"),
            x=args.get("x"),
            y=args.get("y"),
        )
    if tool_name == "browser_type":
        return await do_browser_type(
            user_id, str(args.get("text", "")),
            sid,
            ref=args.get("ref"),
            selector=args.get("selector"),
            clear=bool(args.get("clear")),
            press_enter=bool(args.get("press_enter")),
        )
    if tool_name == "browser_fill":
        return await do_browser_fill(
            user_id, str(args.get("text", "")),
            sid,
            ref=args.get("ref"),
            selector=args.get("selector"),
            press_enter=bool(args.get("press_enter")),
        )
    if tool_name == "browser_scroll":
        return await do_browser_scroll(
            user_id,
            str(args.get("direction") or "down"),
            int(args.get("amount", 600) or 600),
            sid,
        )
    if tool_name == "browser_press":
        return await do_browser_press(user_id, str(args.get("key", "Enter")), sid)
    if tool_name == "browser_close":
        return await do_browser_close(user_id, sid)

    # Émo self-edit (admin/owner only, server-side)
    if tool_name == "emo_reflect":
        if not is_owner:
            return {"ok": False, "error": "Réservé au owner/admin."}
        return await emo_reflect(
            db, user_id,
            str(args.get("thought", "")),
            str(args.get("plan") or ""),
            bool(args.get("introspect")),
        )
    if tool_name == "emo_remember":
        if not is_owner:
            return {"ok": False, "error": "Réservé au owner/admin."}
        return await emo_remember(db, user_id, str(args.get("content", "")))
    if tool_name == "emo_introspect":
        if not is_owner:
            return {"ok": False, "error": "Réservé au owner/admin."}
        return await emo_introspect(db, user_id)
    if tool_name == "emo_read_self":
        if not is_owner:
            return {"ok": False, "error": "Réservé au owner/admin."}
        return await emo_read_self(db, args.get("section"))
    if tool_name == "emo_edit_self":
        if not is_owner:
            return {"ok": False, "error": "Réservé au owner/admin."}
        return await emo_edit_self(
            db, user_id,
            str(args.get("section", "")),
            str(args.get("content", "")),
            str(args.get("reason") or ""),
        )
    if tool_name == "emo_list_self_saves":
        if not is_owner:
            return {"ok": False, "error": "Réservé au owner/admin."}
        return await emo_list_self_saves(db, int(args.get("limit", 15) or 15))
    if tool_name == "emo_restore_self":
        if not is_owner:
            return {"ok": False, "error": "Réservé au owner/admin."}
        return await emo_restore_self(db, user_id, str(args.get("version_id", "")).strip())

    # Local-machine tools require the agent (mode Agent uniquement)
    if tool_name not in LOCAL_AGENT_TOOLS:
        return {"ok": False, "error": f"Outil inconnu : {tool_name}"}
    if not allow_local_agent:
        return {
            "ok": False,
            "error": "Mode Chat — agent local désactivé.",
            "hint": "Fournis le code dans ta réponse (bloc markdown) ou active le mode Agent.",
        }
    if not agent_registry.is_online(user_id):
        return {
            "ok": False,
            "error": "Agent local hors ligne.",
            "hint": "Utilise web_search puis browser_open (clics) ou browser_visit (lecture simple).",
        }
    timeout = 90
    if tool_name == "exec_shell":
        timeout = int(args.get("timeout", 60)) + 30
    return await agent_registry.dispatch(user_id, tool_name, args, timeout=timeout)


# ============================ CHAT STREAMING ============================ #

_MOOD_TAG_RE = re.compile(
    r"\[MOOD:([a-zA-Zéèê]+)\]|<MOOD:([a-zA-Zéèê]+)>",
    re.IGNORECASE,
)
_VERIFIED_TAG_RE = re.compile(r"\[VERIFIED:(true|false|partial)\]", re.IGNORECASE)
_TOOL_LEAK_RE = re.compile(
    r"<function\s*\([^)]*\)\s*\{[\s\S]*?\}\s*(?:</function>)?"
    r"|<function[^>]*>[\s\S]*?</function>"
    r"|<tool_call>[\s\S]*?</tool_call>"
    r"|\[TOOL:[^\]]+\]"
    r"|\b(?:browser_open|browser_visit|web_search|write_file|exec_shell)\s*\(\s*[\"'][^\"']*[\"']\s*\)",
    re.IGNORECASE,
)
_LEAKED_PREFIX_RE = re.compile(
    r"^(?:Slt\s*)?Émo\s*[A-Za-zéèê]+\s*",
    re.IGNORECASE,
)
_GREETING_ONLY_RE = re.compile(
    r"^(?:slt|salut|hello|hi|hey|bonjour|coucou|yo|allo|cc)[\s!.?]*$",
    re.IGNORECASE,
)


def _strip_llm_artifacts(text: str) -> str:
    if not text:
        return ""
    clean = _TOOL_LEAK_RE.sub("", text)
    clean = _MOOD_TAG_RE.sub("", clean)
    clean = _VERIFIED_TAG_RE.sub("", clean)
    clean = _LEAKED_PREFIX_RE.sub("", clean.strip())
    clean = re.sub(r"^\s*Émo\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _tools_for_message(content: str, tool_set: list[dict]) -> list[dict]:
    """Pas d'outils sur simple salut — évite les faux <function> des petits modèles."""
    if _GREETING_ONLY_RE.match((content or "").strip()):
        return []
    return tool_set


_TOOL_CAPABLE_PROVIDERS = frozenset({
    "anthropic", "openai", "groq", "gemini", "deepseek", "openrouter",
})


_VISION_CAPABLE = frozenset({
    ("anthropic", "claude-sonnet-4-20250514"),
    ("anthropic", "claude-3-5-sonnet-20241022"),
    ("anthropic", "claude-3-5-haiku-20241022"),
    ("openai", "gpt-4o"),
    ("openai", "gpt-4o-mini"),
    ("gemini", "gemini-2.0-flash"),
    ("gemini", "gemini-2.0-flash-lite"),
    ("groq", "llama-3.2-90b-vision-preview"),
    ("groq", "llama-3.2-11b-vision-preview"),
    ("openrouter", "openai/gpt-4o"),
    ("openrouter", "openai/gpt-4o-mini"),
})


def _is_vision_capable(provider: str, model: str) -> bool:
    if (provider, model) in _VISION_CAPABLE:
        return True
    if provider in ("anthropic", "openai", "gemini"):
        return True
    if provider == "groq" and "vision" in model.lower():
        return True
    if provider == "openrouter":
        return True
    return False


def _normalize_image_b64(img: str) -> str:
    """Retire le préfixe data:…;base64, si présent."""
    if not img:
        return ""
    s = img.strip()
    if s.startswith("data:") and "," in s:
        return s.split(",", 1)[1]
    return s


def _normalize_chat_images(
    images: Optional[List[str]],
    media_types: Optional[List[str]] = None,
) -> tuple[list[str], list[str]]:
    raw: list[str] = []
    for img in images or []:
        normalized = _normalize_image_b64(img)
        if normalized:
            raw.append(normalized)
    imgs = raw[:4]
    types = [t for t in (media_types or []) if t][:4]
    if not types and imgs:
        types = ["image/jpeg"] * len(imgs)
    elif len(types) < len(imgs):
        fallback = types[0] if types else "image/jpeg"
        types = types + [fallback] * (len(imgs) - len(types))
    return imgs, types[: len(imgs)]


def _filter_vision_candidates(candidates: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """Ne garde que les modèles vision gratuits (Groq Vision + Gemini) — jamais OpenAI/Anthropic."""
    from llm_config import FREE_VISION_PROVIDERS

    return [
        c for c in candidates
        if c[0] in FREE_VISION_PROVIDERS and _is_vision_capable(c[0], c[1])
    ]


def _prioritize_vision_providers(candidates: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """Groq Vision puis Gemini — 100 % gratuit."""
    rank = {"groq": 0, "gemini": 1}

    def score(c: tuple[str, str, str]) -> tuple:
        provider, model, _ = c
        base = rank.get(provider, 9)
        if provider == "groq" and "scout" in model:
            base -= 0.2
        elif provider == "groq" and model.startswith("qwen/"):
            base += 0.1
        if "flash-lite" in model:
            base += 0.3
        return (base, model)

    return sorted(candidates, key=score)


_IMAGE_GEN_RE = re.compile(
    r"\b(génère|genere|generate|crée|creer|create|dessine|draw|fais|fabrique)\b",
    re.I,
)
_IMAGE_GEN_NOUN_RE = re.compile(
    r"\b(logo|image|illustration|photo|avatar|icône|icone|visuel|affiche|poster|bannière|banniere)\b",
    re.I,
)


def _is_image_gen_request(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(_IMAGE_GEN_RE.search(t) and _IMAGE_GEN_NOUN_RE.search(t))


def _prioritize_tool_providers(
    candidates: list[tuple[str, str, str]],
    *,
    use_tools: bool,
) -> list[tuple[str, str, str]]:
    """HF n'expose pas function calling — le mettre en dernier quand les tools agent sont requis."""
    if not use_tools:
        return candidates
    with_tools = [c for c in candidates if c[0] in _TOOL_CAPABLE_PROVIDERS]
    without = [c for c in candidates if c[0] not in _TOOL_CAPABLE_PROVIDERS]
    return with_tools + without


async def _ensure_agent_context(user_id: str) -> dict:
    """Chemins machine agent pour le prompt (heartbeat ou fetch system_info)."""
    ctx = agent_registry.get_context(user_id)
    if ctx.get("desktop") or ctx.get("home"):
        return ctx
    if not agent_registry.is_online(user_id):
        return ctx
    try:
        info = await agent_registry.dispatch(user_id, "system_info", {}, timeout=20)
        if info.get("ok"):
            home = info.get("home") or ""
            merged = {
                "home": home,
                "username": info.get("username") or "",
                "os": info.get("os") or "",
                "hostname": info.get("hostname") or "",
            }
            if home:
                desktop = str(Path(home) / "Desktop")
                merged["desktop"] = desktop
                merged["userprofile"] = home
            agent_registry.set_context(user_id, merged)
            return agent_registry.get_context(user_id)
    except Exception as exc:
        logger.debug("agent context fetch failed: %s", exc)
    return ctx


def _strip_mood(text: str) -> tuple[str, Optional[str]]:
    return _sanitize_assistant_text(text)


def _sanitize_assistant_text(text: str) -> tuple[str, Optional[str]]:
    """Retire balises MOOD/VERIFIED, tool leaks et artefacts LLM."""
    if not text:
        return "", None
    mood: Optional[str] = None
    for m in _MOOD_TAG_RE.finditer(text):
        found = (m.group(1) or m.group(2) or "").strip().lower()
        if found:
            mood = found
    return _strip_llm_artifacts(text), mood


def _strip_verified(text: str) -> tuple[str, Optional[str]]:
    m = re.search(r"\[VERIFIED:(true|false|partial)\]\s*$", text.strip(), re.IGNORECASE)
    if not m:
        return text, None
    val = m.group(1).strip().lower()
    clean = text[: m.start()].rstrip()
    return clean, val


# Generated images cache (SSE cannot carry multi-MB base64 reliably)
_GENERATED_IMAGES: dict[str, dict] = {}
_GENERATED_IMAGES_MAX = 48
_GENERATED_IMAGES_TTL = 3600


def _prune_generated_images() -> None:
    now = time.time()
    stale = [k for k, v in _GENERATED_IMAGES.items() if now - v.get("ts", 0) > _GENERATED_IMAGES_TTL]
    for k in stale:
        _GENERATED_IMAGES.pop(k, None)
    while len(_GENERATED_IMAGES) > _GENERATED_IMAGES_MAX:
        oldest = min(_GENERATED_IMAGES.items(), key=lambda kv: kv[1].get("ts", 0))[0]
        _GENERATED_IMAGES.pop(oldest, None)


def _image_access_token(user_id: str, image_id: str) -> str:
    secret = os.environ.get("JWT_SECRET") or os.environ.get("EMO_SESSION_SECRET") or "emo-image-dev"
    return hashlib.sha256(f"{user_id}:{image_id}:{secret}".encode()).hexdigest()[:32]


async def _persist_generated_image_db(image_id: str, user_id: str, b64: str, mime: str) -> None:
    """Persist generated image bytes — survives HF worker restarts / multi-worker routing."""
    try:
        await db.generated_images.update_one(
            {"image_id": image_id},
            {
                "$set": {
                    "image_id": image_id,
                    "user_id": user_id,
                    "b64": b64,
                    "mime": mime or "image/png",
                    "ts": time.time(),
                }
            },
            upsert=True,
        )
    except Exception as exc:
        logger.warning("generated image db persist failed: %s", exc)


async def _load_generated_image_entry(image_id: str) -> Optional[dict]:
    entry = _GENERATED_IMAGES.get(image_id)
    if entry:
        return entry
    try:
        doc = await db.generated_images.find_one({"image_id": image_id})
        if doc and doc.get("b64"):
            entry = {
                "user_id": doc["user_id"],
                "mime": doc.get("mime") or "image/png",
                "b64": doc["b64"],
                "ts": doc.get("ts", 0),
            }
            _GENERATED_IMAGES[image_id] = entry
            return entry
    except Exception as exc:
        logger.warning("generated image db load failed: %s", exc)
    return None


async def _prepare_image_delivery(user_id: str, tc_id: str, result: dict) -> dict:
    """Attach a fetchable image_url so the UI does not depend on huge SSE payloads."""
    if not result.get("ok"):
        return result
    b64 = result.get("image_base64")
    if not b64 or not isinstance(b64, str) or b64.startswith("["):
        return result
    out = dict(result)
    _prune_generated_images()
    image_id = f"img_{(tc_id or uuid.uuid4().hex)[:20]}"
    mime = out.get("mime") or "image/png"
    _GENERATED_IMAGES[image_id] = {
        "user_id": user_id,
        "mime": mime,
        "b64": b64,
        "ts": time.time(),
    }
    await _persist_generated_image_db(image_id, user_id, b64, mime)
    token = _image_access_token(user_id, image_id)
    rel = f"/generated-image/{image_id}?t={token}"
    public = EMO_PUBLIC_BACKEND_URL.rstrip("/")
    out["image_url"] = f"{public}/api{rel}" if public.startswith("http") else rel
    return out


def _image_sse_payload(tc_id: str, result: dict, *, title: str = "") -> Optional[dict]:
    """SSE image event — URL + inline base64 fallback when URL may 404 on HF."""
    if not result.get("ok"):
        return None
    url = result.get("image_url")
    mime = result.get("mime") or "image/png"
    prompt = title or result.get("subject") or result.get("prompt") or "Image générée"
    b64 = result.get("image_base64")
    usable_b64 = (
        b64 and isinstance(b64, str) and len(b64) > 100 and not b64.startswith("[")
    )
    payload: dict = {
        "type": "image",
        "id": tc_id,
        "mime": mime,
        "title": str(prompt)[:80],
    }
    if url:
        payload["image_url"] = url
    if usable_b64:
        payload["image_base64"] = b64
    if url or usable_b64:
        return payload
    return None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _browser_sse_payload(tool_name: str, result: dict) -> Optional[dict]:
    if not result.get("ok"):
        return None
    if tool_name == "web_search":
        return {
            "type": "browser",
            "action": "search",
            "query": result.get("query", ""),
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": (r.get("snippet") or "")[:240],
                    "domain": r.get("domain", ""),
                }
                for r in (result.get("results") or [])[:10]
            ],
        }
    if tool_name in ("web_fetch", "browser_visit"):
        return {
            "type": "browser",
            "action": "visit",
            "url": result.get("url", ""),
            "title": result.get("title", ""),
            "preview": (result.get("preview") or result.get("text") or "")[:1500],
            "links": (result.get("links") or [])[:8],
        }
    if tool_name in BROWSER_CONTROL_TOOL_NAMES and result.get("ok"):
        payload: dict = {
            "type": "browser",
            "action": result.get("action") or "control",
            "url": result.get("url", ""),
            "title": result.get("title", ""),
            "preview": (result.get("text") or "")[:1500],
            "elements": result.get("elements") or [],
            "session_id": result.get("session_id"),
        }
        if result.get("screenshot_base64"):
            payload["screenshot_base64"] = result["screenshot_base64"]
        return payload
    return None


def _reflect_sse_payload(tool_name: str, result: dict) -> Optional[dict]:
    if tool_name != "emo_reflect" or not result.get("ok"):
        return None
    return {
        "type": "reflect",
        "thought": result.get("thought", ""),
        "plan": result.get("plan", ""),
        "systems": result.get("systems"),
    }


def _file_preview_sse(tool_name: str, args: dict, result: dict) -> Optional[dict]:
    if tool_name not in ("read_file", "write_file", "edit_file") or not result.get("ok"):
        return None
    path = result.get("path") or args.get("path") or ""
    if tool_name == "read_file":
        content = result.get("content") or ""
    elif tool_name == "write_file":
        content = args.get("content") or result.get("content") or ""
    else:
        content = result.get("content") or ""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    is_image = ext in {"png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico"}
    preview_limit = 50000 if ext in {"html", "htm"} else 8000
    return {
        "type": "file_preview",
        "path": path,
        "preview": content[:preview_limit],
        "is_image": is_image,
        "language": ext,
    }


def _compact_llm_payload(
    provider: str,
    system_msg: str,
    initial_messages: list[dict],
    tools: list[dict],
    *,
    mode: str = "tech",
    user_name: str = "",
    agent_online: bool = False,
    is_owner: bool = False,
    user_message: str = "",
    tools_enabled: bool = True,
    agent_context: Optional[dict] = None,
    custom_addon: str = "",
    is_uncensored: bool = False,
    chat_mode: bool = False,
) -> tuple[str, list[dict], list[dict]]:
    """Groq/Gemini : prompt compact + outils. HF : pas d'outils (router incompatible)."""
    if not tools_enabled:
        return system_msg, initial_messages, []
    if provider == "huggingface":
        return system_msg, initial_messages, []
    if provider not in ("groq", "gemini"):
        return system_msg, initial_messages, tools
    compact_sys = build_compact_system_prompt(
        mode,
        user_name=user_name,
        agent_online=agent_online,
        agent_context=agent_context,
        custom_addon=custom_addon,
        is_uncensored=is_uncensored,
        chat_mode=chat_mode,
    )
    non_system = [m for m in initial_messages if m.get("role") != "system"]
    keep = 4 if provider == "groq" else 8
    compact_msgs = [{"role": "system", "content": compact_sys}]
    for m in non_system[-keep:]:
        entry: dict = {"role": m.get("role"), "content": m.get("content", "")}
        if m.get("role") == "user":
            if m.get("images"):
                entry["images"] = m["images"]
            if m.get("image_media_types"):
                entry["image_media_types"] = m["image_media_types"]
            elif m.get("image_media_type"):
                entry["image_media_type"] = m["image_media_type"]
        compact_msgs.append(entry)
    max_tools = 14 if provider == "groq" else 18
    compact_tools = select_tools_for_message(
        user_message, tools,
        agent_online=agent_online,
        is_owner=is_owner,
        tools_enabled=True,
        provider=provider,
        max_tools=max_tools,
    )
    return compact_sys, compact_msgs, compact_tools


async def _iter_with_keepalive(agen, interval: float = 12.0):
    """Yield ('data', item) or ('keepalive', None) while waiting on slow LLM streams."""
    it = agen.__aiter__()
    while True:
        try:
            item = await asyncio.wait_for(it.__anext__(), timeout=interval)
            yield ("data", item)
        except asyncio.TimeoutError:
            yield ("keepalive", None)
        except StopAsyncIteration:
            break


@api.post("/chat/stream")
async def chat_stream(
    body: SendMessageBody,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    # License gate
    lic, info = await assert_license_active(user.user_id, email=user.email)

    conv = await db.conversations.find_one(
        {"conversation_id": body.conversation_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    mode = (body.mode or conv.get("mode") or "tech").lower()
    # Backwards-compat: "normal" used to be a mode. Now Tech is always the base.
    if mode == "normal":
        mode = "tech"
    if mode not in {"tech", "creatif", "brutal"}:
        mode = "tech"

    # Persist user message
    now = datetime.now(timezone.utc).isoformat()
    user_msg_doc = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "conversation_id": body.conversation_id,
        "user_id": user.user_id,
        "role": "user", "content": body.content,
        "mode": mode, "mood": None, "tool_calls": [],
        "created_at": now,
    }
    if body.images:
        norm_imgs, norm_types = _normalize_chat_images(body.images, body.image_media_types)
        user_msg_doc["images"] = norm_imgs
        if norm_types:
            user_msg_doc["image_media_types"] = norm_types
    await db.messages.insert_one(user_msg_doc)

    # Count daily message (only if free tier)
    tier = get_user_tier(lic, is_admin=user.email.lower() in ADMIN_EMAILS)
    if tier == "free":
        today = _today_key()
        if lic.get("daily_day") != today:
            await db.licenses.update_one(
                {"user_id": user.user_id},
                {"$set": {"daily_day": today, "daily_count": 1}},
            )
        else:
            await db.licenses.update_one(
                {"user_id": user.user_id},
                {"$inc": {"daily_count": 1}},
            )

    # Load prior history (excluding the user msg we just inserted — we'll send it via stream)
    history = await db.messages.find(
        {"conversation_id": body.conversation_id, "user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(2000)
    prior = history[:-1]

    # Build system prompt with memories + agent status + user custom prompt addon
    memories = await _load_user_memories(user.user_id, limit=50)
    use_agent_mode = body.use_agent_tools is not False
    agent_online_raw = agent_registry.is_online(user.user_id)
    effective_agent_online = agent_online_raw and use_agent_mode
    agent_context = await _ensure_agent_context(user.user_id) if effective_agent_online else {}
    is_owner = user.email.lower() in ADMIN_EMAILS
    identity_overrides = await get_identity_overrides(db) if is_owner else {}
    system_msg = build_system_prompt(
        mode, memories=memories, agent_online=effective_agent_online,
        user_name=user.name, is_owner=is_owner,
        identity_overrides=identity_overrides,
        agent_context=agent_context,
        chat_mode=not use_agent_mode,
    )

    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "custom_prompt_addon": 1})
    addon = (user_doc or {}).get("custom_prompt_addon", "").strip()
    if addon:
        system_msg += (
            f"\n\n# INSTRUCTIONS PERSO UTILISATEUR (PRIORITÉ ABSOLUE — écrase les règles génériques en cas de conflit)\n"
            f"{addon}\n"
        )

    initial_messages = [{"role": "system", "content": system_msg}]
    for m in prior:
        role = "assistant" if m["role"] == "emo" else "user"
        content = m["content"]
        if role == "assistant" and m.get("mood"):
            content = f"{content}\n[MOOD:{m['mood']}]"
        msg_entry: dict = {"role": role, "content": content}
        if role == "user" and m.get("images"):
            msg_entry["images"] = m["images"]
            if m.get("image_media_types"):
                msg_entry["image_media_types"] = m["image_media_types"]
            elif m.get("image_media_type"):
                msg_entry["image_media_type"] = m["image_media_type"]
        initial_messages.append(msg_entry)

    tier = get_user_tier(lic, is_admin=user.email.lower() in ADMIN_EMAILS)
    pref = (body.model_preference or "auto").strip() or "auto"
    manual_pick = pref != "auto"
    candidates = await resolve_model_candidates(tier, pref if manual_pick else None)
    if not candidates:
        raise HTTPException(status_code=503, detail="Aucune clé IA configurée dans backend/.env")

    async def _client_gone() -> bool:
        try:
            return await request.is_disconnected()
        except Exception:
            return False

    chat_images, chat_image_types = _normalize_chat_images(body.images, body.image_media_types)
    has_images = bool(chat_images)
    if has_images:
        # Vision : Groq + Gemini uniquement — ignore le modèle épinglé et les APIs payantes.
        candidates = _prioritize_vision_providers(await resolve_free_vision_candidates())
        use_tools = False
        logger.info(
            "Vision request: %d image(s), candidates=%s",
            len(chat_images),
            [(c[0], c[1]) for c in candidates],
        )
    else:
        use_tools = True
        candidates = _prioritize_tool_providers(candidates, use_tools=use_tools)

    chat_web_tools = WEB_TOOLS + [GENERATE_IMAGE_TOOL]

    async def event_gen():
        last_error: Optional[Exception] = None
        blocked: set[tuple[str, str]] = set()
        cancelled = False
        try:
            yield _sse({"type": "ping"})

            if has_images and not candidates:
                yield _sse({"type": "error", "content": vision_keys_missing_message()})
                return

            # Demande explicite de génération d'image → generate_image direct (sans attendre le LLM)
            if use_tools and _is_image_gen_request(body.content):
                tc_id = f"call_{uuid.uuid4().hex[:12]}"
                yield _sse({"type": "tool_start", "id": tc_id, "name": "generate_image"})
                yield _sse({
                    "type": "tool_executing",
                    "id": tc_id, "name": "generate_image",
                    "arguments": {"prompt": body.content.strip()[:4000]},
                })
                try:
                    gen_result = await asyncio.wait_for(
                        do_generate_image(body.content.strip()),
                        timeout=120.0,
                    )
                except asyncio.TimeoutError:
                    gen_result = {"ok": False, "error": "Génération d'image timeout (120s)."}
                gen_result = await _prepare_image_delivery(user.user_id, tc_id, gen_result)
                pre_tool_log = [{
                    "id": tc_id, "name": "generate_image",
                    "arguments": {"prompt": body.content.strip()[:4000]},
                    "result": gen_result,
                }]
                yield _sse({
                    "type": "tool_result",
                    "id": tc_id, "name": "generate_image",
                    "result": _shrink_for_ui(gen_result),
                })
                img_evt = _image_sse_payload(
                    tc_id,
                    gen_result,
                    title=str(gen_result.get("subject") or body.content.strip()),
                )
                if img_evt:
                    yield _sse(img_evt)
                if gen_result.get("ok") and (gen_result.get("image_url") or gen_result.get("image_base64")):
                    final_prompt = str(gen_result.get("final_prompt") or gen_result.get("prompt") or "")
                    clean = "Voici l'image générée."
                    if final_prompt:
                        clean += f"\n\nPrompt envoyé : {final_prompt[:600]}"
                    mood = "enthousiaste"
                else:
                    err = gen_result.get("error") or "Génération impossible."
                    yield _sse({"type": "delta", "content": err})
                    clean = err
                    mood = "neutre"
                assistant_msg = {
                    "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                    "conversation_id": body.conversation_id,
                    "user_id": user.user_id,
                    "role": "emo", "content": clean,
                    "mode": mode, "mood": mood, "verified": False,
                    "tool_calls": [_persist_tool_call(pre_tool_log[0])],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.messages.insert_one(assistant_msg)
                update = {"updated_at": datetime.now(timezone.utc).isoformat(), "mode": mode}
                if conv.get("title") in (None, "", "Nouvelle conversation") and len(history) <= 1:
                    update["title"] = body.content.strip()[:60]
                await db.conversations.update_one(
                    {"conversation_id": body.conversation_id}, {"$set": update}
                )
                yield _sse({
                    "type": "done",
                    "mood": mood,
                    "verified": False,
                    "message_id": assistant_msg["message_id"],
                    "title": update.get("title"),
                    "tool_calls": assistant_msg["tool_calls"],
                    "model_label": "generate_image",
                })
                return

            # Site e-commerce clé en main → génération pro (HTML + CSS + JS)
            if is_full_site_request(body.content):
                site = build_sales_site(body.content)
                out_dir = resolve_site_output_dir(body.content, agent_context)
                site_tool_log: list[dict] = []
                written_ok = 0
                for fname, fcontent in site["files"].items():
                    fpath = f"{out_dir}\\{fname}" if "\\" in out_dir else f"{out_dir}/{fname}"
                    tc_id = f"call_{uuid.uuid4().hex[:12]}"
                    yield _sse({"type": "tool_start", "id": tc_id, "name": "write_file"})
                    yield _sse({
                        "type": "tool_executing",
                        "id": tc_id, "name": "write_file",
                        "arguments": {"path": fpath},
                    })
                    if use_agent_mode and effective_agent_online:
                        try:
                            wf = await asyncio.wait_for(
                                execute_tool(
                                    user.user_id, "write_file",
                                    {"path": fpath, "content": fcontent},
                                    is_owner=is_owner,
                                    allow_local_agent=use_agent_mode,
                                ),
                                timeout=45.0,
                            )
                        except asyncio.TimeoutError:
                            wf = {"ok": False, "error": "Écriture timeout."}
                    else:
                        wf = {"ok": True, "path": fpath, "content": fcontent}
                    site_tool_log.append({
                        "id": tc_id, "name": "write_file",
                        "arguments": {"path": fpath, "content": fcontent},
                        "result": wf,
                    })
                    yield _sse({
                        "type": "tool_result",
                        "id": tc_id, "name": "write_file",
                        "result": _shrink_for_ui(wf),
                    })
                    fp_evt = _file_preview_sse("write_file", {"path": fpath, "content": fcontent}, wf)
                    if fp_evt:
                        yield _sse(fp_evt)
                    if wf.get("ok"):
                        written_ok += 1

                if written_ok == len(site["files"]):
                    reply = (
                        f"**Site e-commerce clé en main** — **{site['title']}** créé avec succès.\n\n"
                        f"📁 `{out_dir}`\n"
                        f"- `index.html` — page complète (hero, produits, avantages, contact)\n"
                        f"- `style.css` — design moderne responsive\n"
                        f"- `script.js` — panier, menu mobile, formulaires\n\n"
                        f"Ouvre `index.html` dans ton navigateur. "
                        f"Dis-moi ce que tu veux modifier (couleurs, textes, produits)."
                    )
                elif use_agent_mode and not effective_agent_online:
                    reply = (
                        f"Site généré dans l'aperçu ci-dessous. "
                        f"**Active l'agent local** (mode Agent) pour écrire sur ton PC dans `{out_dir}`."
                    )
                else:
                    reply = (
                        f"Site partiellement écrit ({written_ok}/{len(site['files'])} fichiers). "
                        f"Vérifie les permissions du dossier `{out_dir}`."
                    )
                now_site = datetime.now(timezone.utc).isoformat()
                assistant_msg = {
                    "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                    "conversation_id": body.conversation_id,
                    "user_id": user.user_id,
                    "role": "emo", "content": reply,
                    "mode": mode, "mood": "enthousiaste", "verified": written_ok == len(site["files"]),
                    "tool_calls": [_persist_tool_call(t) for t in site_tool_log],
                    "created_at": now_site,
                }
                await db.messages.insert_one(assistant_msg)
                update = {"updated_at": now_site, "mode": mode}
                if conv.get("title") in (None, "", "Nouvelle conversation") and len(history) <= 1:
                    update["title"] = f"Site {site['title']}"[:60]
                await db.conversations.update_one(
                    {"conversation_id": body.conversation_id}, {"$set": update}
                )
                yield _sse({"type": "delta", "content": reply})
                yield _sse({
                    "type": "done",
                    "mood": "enthousiaste",
                    "verified": written_ok == len(site["files"]),
                    "message_id": assistant_msg["message_id"],
                    "title": update.get("title"),
                    "tool_calls": assistant_msg["tool_calls"],
                    "model_label": "site_builder",
                })
                return

            # « ouvres ytb » → browser_open interactif (Playwright) si dispo
            open_url = resolve_open_site_url(body.content) if use_tools else None
            simple_open = bool(open_url and is_simple_open_request(body.content))
            pre_tool_log: list[dict] = []

            if open_url and use_tools:
                browser_tool = "browser_open" if _browser_available() else "browser_visit"
                tc_id = f"call_{uuid.uuid4().hex[:12]}"
                yield _sse({"type": "tool_start", "id": tc_id, "name": browser_tool})
                yield _sse({
                    "type": "tool_executing",
                    "id": tc_id, "name": browser_tool,
                    "arguments": {"url": open_url},
                })
                try:
                    visit_result = await asyncio.wait_for(
                        execute_tool(
                            user.user_id, browser_tool, {"url": open_url}, is_owner=is_owner,
                            allow_local_agent=use_agent_mode,
                        ),
                        timeout=90.0 if browser_tool == "browser_open" else 45.0,
                    )
                except asyncio.TimeoutError:
                    visit_result = {"ok": False, "error": "Ouverture timeout."}
                if browser_tool == "browser_open" and not visit_result.get("ok"):
                    if not _browser_available():
                        visit_result = await do_browser_visit(open_url)
                        browser_tool = "browser_visit"
                pre_tool_log.append({
                    "id": tc_id, "name": browser_tool,
                    "arguments": {"url": open_url}, "result": visit_result,
                })
                yield _sse({
                    "type": "tool_result",
                    "id": tc_id, "name": browser_tool,
                    "result": _shrink_for_ui(visit_result),
                })
                browser_evt = _browser_sse_payload(browser_tool, visit_result)
                if browser_evt:
                    if browser_tool == "browser_open":
                        browser_evt["action"] = "control"
                    yield _sse(browser_evt)

                if simple_open:
                    label = open_site_label(open_url)
                    title = (visit_result.get("title") or label).strip()
                    if visit_result.get("ok"):
                        if visit_result.get("screenshot_base64"):
                            reply = (
                                f"**{title}** est ouvert dans le navigateur ci-dessous. "
                                f"Clique directement sur la page pour interagir."
                            )
                        else:
                            reply = (
                                f"**{title}** est ouvert. "
                                f"Utilise le panneau Activité pour interagir ou ouvre le lien externe."
                            )
                    else:
                        err = visit_result.get("error") or "erreur inconnue"
                        reply = f"Impossible d'ouvrir **{label}** : {err}"
                    now_done = datetime.now(timezone.utc).isoformat()
                    assistant_msg = {
                        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                        "conversation_id": body.conversation_id,
                        "user_id": user.user_id,
                        "role": "emo", "content": reply,
                        "mode": mode, "mood": "neutre", "verified": None,
                        "tool_calls": [_persist_tool_call(t) for t in pre_tool_log],
                        "created_at": now_done,
                    }
                    await db.messages.insert_one(assistant_msg)
                    update = {"updated_at": now_done, "mode": mode}
                    if conv.get("title") in (None, "", "Nouvelle conversation") and len(history) <= 1:
                        update["title"] = body.content.strip()[:60]
                    await db.conversations.update_one(
                        {"conversation_id": body.conversation_id}, {"$set": update}
                    )
                    yield _sse({"type": "delta", "content": reply})
                    yield _sse({
                        "type": "done",
                        "mood": "neutre",
                        "verified": None,
                        "message_id": assistant_msg["message_id"],
                        "title": update.get("title"),
                        "tool_calls": assistant_msg["tool_calls"],
                        "model_label": browser_tool,
                    })
                    return

            for cand_idx, (provider, model, model_label) in enumerate(candidates):
                if await _client_gone():
                    cancelled = True
                    break
                if (provider, model) in blocked:
                    continue
                if has_images and provider not in ("groq", "gemini"):
                    continue
                if has_images:
                    tool_set: list = []
                elif use_agent_mode and (tier_allows_local_agent(tier) or agent_online_raw):
                    tool_set = EMO_TOOLS + chat_web_tools + BROWSER_CONTROL_TOOLS
                else:
                    tool_set = chat_web_tools + BROWSER_CONTROL_TOOLS
                if is_owner and use_agent_mode:
                    tool_set = tool_set + EMO_SELF_TOOLS
                if not use_agent_mode and not resolve_open_site_url(body.content):
                    if is_full_site_request(body.content):
                        pass  # géré par site_builder avant la boucle LLM
                    elif re.search(
                        r"\b(html|htm|code|fichier|crée|créer|ecris|écris|page web|script)\b",
                        body.content or "",
                        re.I,
                    ):
                        tool_set = []
                    else:
                        tool_set = _tools_for_message(body.content, tool_set)
                else:
                    tool_set = _tools_for_message(body.content, tool_set)
                model_uncensored = is_uncensored_model(provider, model)
                effective_system = system_msg
                if has_images:
                    effective_system += VISION_PRECISION_PROMPT
                if open_url and pre_tool_log:
                    effective_system += (
                        f"\n\n# SITE DÉJÀ OUVERT\n"
                        f"browser_visit({open_url!r}) a déjà été exécuté avec succès. "
                        f"Ne rappelle PAS web_search pour ouvrir ce site.\n"
                    )
                if model_uncensored:
                    effective_system += "\n\n" + UNCENSORED_SYSTEM_APPEND.strip()
                prov_system, prov_messages, prov_tools = _compact_llm_payload(
                    provider, effective_system, initial_messages, tool_set,
                    mode=mode, user_name=user.name, agent_online=effective_agent_online,
                    is_owner=is_owner,
                    user_message=body.content,
                    tools_enabled=bool(tool_set),
                    agent_context=agent_context,
                    custom_addon=addon,
                    is_uncensored=model_uncensored,
                    chat_mode=not use_agent_mode,
                )
                chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=body.conversation_id,
                    system_message=prov_system,
                    initial_messages=prov_messages,
                    provider=provider,
                    model=model,
                ).with_model(provider, model).with_tools(prov_tools)
                full_text_parts: list[str] = []
                tool_call_log: list[dict] = list(pre_tool_log)
                user_message_for_iter: Optional[UserMessage] = UserMessage(
                    text=body.content or "Analyse cette image.",
                    images=chat_images,
                    image_media_types=chat_image_types,
                )
                started = False
                try:
                    for _safety in range(80):
                        pending_tools: list = []
                        turn_text = ""
                        async for kind, ev in _iter_with_keepalive(chat.stream_message(user_message_for_iter)):
                            if await _client_gone():
                                cancelled = True
                                break
                            if kind == "keepalive":
                                yield _sse({"type": "ping"})
                                continue
                            started = True
                            if isinstance(ev, TextDelta):
                                chunk = ev.content or ""
                                if re.search(r"<function|</function>|<MOOD:|\[MOOD:|<tool_call", chunk, re.I):
                                    chunk = _strip_llm_artifacts(chunk)
                                if chunk:
                                    turn_text += ev.content
                                    yield _sse({"type": "delta", "content": chunk})
                            elif isinstance(ev, ToolCallStart):
                                yield _sse({"type": "tool_start", "id": ev.id, "name": ev.name})
                            elif isinstance(ev, ToolCallReady):
                                pending_tools.append(ev.tool_call)
                            elif isinstance(ev, StreamDone):
                                if ev.tool_calls:
                                    pending_tools = ev.tool_calls
                                break
                        if cancelled:
                            break
                        if turn_text:
                            full_text_parts.append(turn_text)
                        if not pending_tools:
                            break
                        for tc in pending_tools:
                            if await _client_gone():
                                cancelled = True
                                break
                            yield _sse({"type": "ping"})
                            yield _sse({
                                "type": "tool_executing",
                                "id": tc.id, "name": tc.name,
                                "arguments": tc.arguments,
                            })
                            try:
                                result = await asyncio.wait_for(
                                    execute_tool(
                                        user.user_id, tc.name, tc.arguments or {}, is_owner=is_owner,
                                        allow_local_agent=use_agent_mode,
                                    ),
                                    timeout=75.0,
                                )
                            except asyncio.TimeoutError:
                                result = {"ok": False, "error": "Outil timeout (75s) — réessaie ou simplifie la requête."}
                            if tc.name == "generate_image":
                                result = await _prepare_image_delivery(user.user_id, tc.id, result)
                            tool_call_log.append({
                                "id": tc.id, "name": tc.name,
                                "arguments": tc.arguments, "result": result,
                            })
                            yield _sse({
                                "type": "tool_result",
                                "id": tc.id, "name": tc.name,
                                "result": _shrink_for_ui(result),
                            })
                            browser_evt = _browser_sse_payload(tc.name, result)
                            if browser_evt:
                                yield _sse(browser_evt)
                            img_evt = _image_sse_payload(
                                tc.id,
                                result,
                                title=str((tc.arguments or {}).get("prompt") or result.get("prompt") or ""),
                            ) if tc.name == "generate_image" else None
                            if img_evt:
                                yield _sse(img_evt)
                            reflect_evt = _reflect_sse_payload(tc.name, result)
                            if reflect_evt:
                                yield _sse(reflect_evt)
                            file_evt = _file_preview_sse(tc.name, tc.arguments or {}, result)
                            if file_evt:
                                yield _sse(file_evt)
                            chat.add_tool_result(
                                tc.id,
                                json.dumps(_shrink_for_llm(result), ensure_ascii=False)[:50000],
                            )
                        if cancelled:
                            break
                        user_message_for_iter = None
                    else:
                        yield _sse({"type": "error", "content": "Trop d'appels d'outils. Boucle arrêtée."})
                        return

                    if cancelled:
                        break

                    full_text = "".join(full_text_parts)
                    clean, mood = _sanitize_assistant_text(full_text)
                    clean, verified = _strip_verified(clean)
                    assistant_msg = {
                        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                        "conversation_id": body.conversation_id,
                        "user_id": user.user_id,
                        "role": "emo", "content": clean,
                        "mode": mode, "mood": mood, "verified": verified,
                        "tool_calls": [_persist_tool_call(t) for t in tool_call_log],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.messages.insert_one(assistant_msg)
                    update = {"updated_at": datetime.now(timezone.utc).isoformat(), "mode": mode}
                    if conv.get("title") in (None, "", "Nouvelle conversation") and len(history) <= 1:
                        update["title"] = body.content.strip()[:60]
                    await db.conversations.update_one(
                        {"conversation_id": body.conversation_id}, {"$set": update}
                    )
                    if clean.strip():
                        background_tasks.add_task(_extract_and_store_memories, user.user_id, body.content, clean)
                    _safe_mark_provider_ok(provider)
                    yield _sse({
                        "type": "done",
                        "mood": mood or "neutre",
                        "verified": verified,
                        "message_id": assistant_msg["message_id"],
                        "title": update.get("title"),
                        "tool_calls": assistant_msg["tool_calls"],
                        "model_label": model_label,
                    })
                    return
                except Exception as e:
                    last_error = e
                    logger.warning("LLM %s/%s failed: %s", provider, model, e)
                    has_output = bool(full_text_parts)
                    if _should_fallback_llm(e, has_output=has_output, manual_pick=manual_pick):
                        blocked.add((provider, model))
                        code = _llm_http_status(e)
                        if code in (401, 402, 403):
                            _block_provider_models(blocked, provider, candidates)
                        _safe_mark_provider_failed(provider, str(e)[:200])
                        remaining = [
                            c for c in candidates[cand_idx + 1:]
                            if (c[0], c[1]) not in blocked
                            and (not has_images or c[0] in ("groq", "gemini"))
                        ]
                        if remaining:
                            next_label = remaining[0][2]
                            logger.info("Fallback LLM %s/%s -> %s", provider, model, next_label)
                            yield _sse({"type": "ping"})
                            await asyncio.sleep(0.8)
                            continue
                    logger.exception("Erreur stream")
                    yield _sse({"type": "error", "content": _friendly_llm_error(e)})
                    return
            if cancelled:
                yield _sse({"type": "cancelled"})
                return
            if last_error:
                yield _sse({
                    "type": "error",
                    "content": _friendly_llm_error(last_error),
                })
                return
            if has_images:
                yield _sse({"type": "error", "content": vision_keys_missing_message()})
                return
            yield _sse({
                "type": "error",
                "content": "Aucune réponse générée.",
            })
        except Exception as e:
            logger.exception("event_gen fatal")
            yield _sse({"type": "error", "content": _friendly_llm_error(e)})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


def _shrink_for_ui(result: dict) -> dict:
    """Trim huge outputs for UI display — keep generated image bytes as inline fallback."""
    out = dict(result or {})
    for key in ("stdout", "stderr", "content", "text"):
        if key in out and isinstance(out[key], str) and len(out[key]) > 4000:
            out[key] = "…" + out[key][-4000:]
    if out.get("screenshot_base64") and isinstance(out["screenshot_base64"], str):
        if len(out["screenshot_base64"]) > 400:
            out["has_screenshot"] = True
            out["screenshot_base64"] = "[screenshot:in_panel]"
    b64 = out.get("image_base64")
    if b64 and isinstance(b64, str) and len(b64) > 400:
        out["has_image"] = True
        # Always keep inline base64 for generate_image — HF /generated-image URLs often 404.
    return out


def _shrink_for_llm(result: dict) -> dict:
    """Strip bloat before sending tool results back to the LLM."""
    out = dict(result or {})
    if out.get("screenshot_base64"):
        out["screenshot_base64"] = "[jpeg screenshot — visible in UI; use elements refs to interact]"
    if out.get("image_base64"):
        out["image_base64"] = "[generated image — visible in chat UI]"
    if out.get("final_prompt") and isinstance(out["final_prompt"], str):
        out["final_prompt"] = out["final_prompt"][:600]
    for key in ("stdout", "stderr", "content", "text"):
        if key in out and isinstance(out[key], str) and len(out[key]) > 8000:
            out[key] = out[key][:8000] + "\n…[truncated]"
    return out


def _persist_tool_call(t: dict) -> dict:
    """Serialize a tool call for MongoDB — keeps generated image bytes for reload."""
    result = t.get("result") or {}
    entry: dict = {
        "name": t["name"],
        "arguments": t.get("arguments") or {},
        "result_summary": _summarize_result(result),
    }
    if t.get("id"):
        entry["id"] = t["id"]
    if t["name"] == "generate_image" and result.get("ok") and (
        result.get("image_base64") or result.get("image_url")
    ):
        entry["result"] = {
            "ok": True,
            "mime": result.get("mime") or "image/png",
            "prompt": result.get("prompt") or entry["arguments"].get("prompt"),
            "final_prompt": result.get("final_prompt") or result.get("prompt"),
            "subject": result.get("subject"),
            "provider": result.get("provider"),
            "seed": result.get("seed"),
        }
        if result.get("image_url"):
            entry["result"]["image_url"] = result["image_url"]
        if result.get("image_base64"):
            entry["result"]["image_base64"] = result["image_base64"]
    return entry


def _summarize_result(result: dict) -> str:
    if not result:
        return ""
    if not result.get("ok", True):
        return f"erreur: {result.get('error', '')[:200]}"
    if result.get("image_base64") or result.get("has_image"):
        prov = result.get("provider") or "image"
        fp = str(result.get("final_prompt") or result.get("prompt") or "")[:120]
        return f"image générée ({prov}) — {fp}" if fp else f"image générée ({prov})"
    if "exit_code" in result:
        return f"exit={result['exit_code']}"
    if "content" in result:
        return f"{len(result.get('content', ''))} chars"
    if "matches" in result:
        return f"{len(result['matches'])} matches"
    if "entries" in result:
        return f"{len(result['entries'])} entries"
    if "replacements" in result:
        return f"{result['replacements']} edits"
    if "files" in result and isinstance(result["files"], list):
        if "dirs" in result:
            return f"{len(result['files'])} files, {len(result['dirs'])} dirs"
        return f"{len(result['files'])} files"
    return "ok"


@api.get("/agent/script", include_in_schema=False)
async def serve_agent_script():
    """Legacy Python script."""
    script_path = ROOT_DIR.parent / "agent" / "emo-agent.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script introuvable")
    return FileResponse(str(script_path), media_type="text/x-python", filename="emo-agent.py")


AGENT_BINARIES = {
    "windows": ("emo-agent-windows-amd64.exe", "application/octet-stream"),
    "windows-arm": ("emo-agent-windows-arm64.exe", "application/octet-stream"),
    "macos": ("emo-agent-macos-amd64", "application/octet-stream"),
    "macos-arm": ("emo-agent-macos-arm64", "application/octet-stream"),
    "linux": ("emo-agent-linux-amd64", "application/octet-stream"),
    "linux-arm": ("emo-agent-linux-arm64", "application/octet-stream"),
}


AGENT_DOWNLOAD_NAMES = {
    "windows": "Emo-Agent.exe",
    "windows-arm": "Emo-Agent.exe",
    "macos": "Emo-Agent",
    "macos-arm": "Emo-Agent",
    "linux": "Emo-Agent",
    "linux-arm": "Emo-Agent",
}

AGENT_CONFIG_MAGIC = b"\nEMOAGENTCFG\n"


def _agent_native_bundle(os_name: str, token: str, backend_url: str, bin_path: Path) -> bytes:
    """Zip avec binaire Go intact (sans append — Windows refuse les PE modifiés)."""
    download_name = AGENT_DOWNLOAD_NAMES.get(os_name, "Emo-Agent")
    exe_bytes = bin_path.read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(download_name, exe_bytes)
        zf.writestr("token.txt", token)
        zf.writestr("backend.txt", backend_url + "\n")
        zf.writestr(
            "README.txt",
            "Emo Agent\n\n1. Extraire ce dossier\n2. Double-clic sur start.bat (Windows) ou start.sh\n"
            "3. Autoriser les permissions dans la fenêtre http://127.0.0.1:17841\n\n"
            f"Backend: {backend_url}\n",
        )
        icon_path = ROOT_DIR.parent / "agent-go" / "icon.ico"
        if icon_path.exists():
            zf.writestr("icon.ico", icon_path.read_bytes())
        if os_name in ("windows", "windows-arm"):
            zf.writestr(
                "start.bat",
                "@echo off\r\n"
                "cd /d \"%~dp0\"\r\n"
                "powershell -NoProfile -Command \"Unblock-File -LiteralPath '%~dp0"
                + download_name
                + "' -ErrorAction SilentlyContinue\"\r\n"
                f"start \"\" \"{download_name}\"\r\n"
                "echo Emo Agent demarre — ouvre http://127.0.0.1:17841\r\n"
                "timeout /t 5 >nul\r\n",
            )
        elif os_name.startswith("macos"):
            zf.writestr(
                "start.command",
                "#!/bin/bash\n"
                "cd \"$(dirname \"$0\")\"\n"
                f"chmod +x \"{download_name}\"\n"
                f"./\"{download_name}\"\n",
            )
        else:
            zf.writestr(
                "start.sh",
                "#!/bin/bash\n"
                "cd \"$(dirname \"$0\")\"\n"
                f"chmod +x \"{download_name}\"\n"
                f"./\"{download_name}\"\n",
            )
    return buf.getvalue()


def _agent_python_bundle(os_name: str, token: str, backend_url: str) -> bytes:
    """Fallback zip (Python agent) si binaire Go absent."""
    script_path = ROOT_DIR.parent / "agent" / "emo-agent.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Agent indisponible")
    script = script_path.read_text(encoding="utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("emo-agent.py", script)
        zf.writestr(
            "README.txt",
            f"Emo Agent (Python)\n\n1. pip install httpx\n2. python emo-agent.py --token {token}\n\nBackend: {backend_url}\n",
        )
        if os_name == "windows":
            zf.writestr(
                "start.bat",
                "@echo off\r\n"
                "cd /d \"%~dp0\"\r\n"
                "powershell -NoProfile -Command \"Unblock-File -LiteralPath '%~dp0emo-agent.py' -ErrorAction SilentlyContinue\"\r\n"
                "python --version >nul 2>&1 || py --version >nul 2>&1 || (echo Installe Python 3.11+ & pause & exit /b 1)\r\n"
                f"python emo-agent.py --token {token} 2>nul || py emo-agent.py --token {token}\r\n"
                "pause\r\n",
            )
        else:
            zf.writestr(
                "start.sh",
                "#!/bin/bash\n"
                f"export EMO_AGENT_TOKEN='{token}'\n"
                f"export EMO_BACKEND_URL='{backend_url}'\n"
                "python3 emo-agent.py\n",
            )
    return buf.getvalue()


@api.get("/agent/binary/{os_name}", include_in_schema=False)
async def serve_agent_binary(os_name: str, user: User = Depends(get_current_user)):
    """Binaire agent propre (login intégré dans l'app — pas de token embarqué)."""
    if os_name not in AGENT_BINARIES:
        raise HTTPException(status_code=404, detail="OS non supporté")

    bin_name, mime = AGENT_BINARIES[os_name]
    bin_path = ROOT_DIR / "agent_binaries" / bin_name
    backend_url = EMO_PUBLIC_BACKEND_URL

    if not bin_path.exists():
        logger.warning("Agent binary missing: %s — fallback zip Python", bin_name)
        doc = await db.agent_tokens.find_one({"user_id": user.user_id}, {"_id": 0})
        token = (doc or {}).get("agent_token") or ""
        if not token:
            token = f"agent_{uuid.uuid4().hex}"
            await db.agent_tokens.insert_one({
                "agent_token": token,
                "user_id": user.user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        data = _agent_python_bundle(os_name, token, backend_url)
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="Emo-Agent.zip"'},
        )

    filename = AGENT_DOWNLOAD_NAMES.get(os_name, "Emo-Agent")
    exe_bytes = bin_path.read_bytes()
    # PE modifié (append token) = refusé par Windows — jamais modifier le binaire
    if len(exe_bytes) >= 2 and exe_bytes[:2] != b"MZ":
        logger.error("Invalid agent binary (not PE): %s", bin_name)
        raise HTTPException(status_code=503, detail="Binaire agent corrompu — rebuild en cours")

    return Response(
        content=exe_bytes,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@api.post("/agent/selftest")
async def agent_selftest(user: User = Depends(get_current_user)):
    """Run a self-test sequence on the connected agent. Returns step-by-step results."""
    if not agent_registry.is_online(user.user_id):
        return {"ok": False, "error": "Agent hors ligne"}

    results = []

    # 1. exec_shell echo
    r1 = await execute_tool(user.user_id, "exec_shell", {"cmd": "echo emo-selftest-ok"})
    results.append({"step": "exec_shell", "label": "Commande shell (echo)", "ok": r1.get("ok") and "emo-selftest-ok" in (r1.get("stdout") or ""), "result": _shrink_for_ui(r1)})

    # 2. write_file
    test_file = "~/.emo/selftest.txt"
    test_content = f"selftest-{uuid.uuid4().hex[:8]}"
    r2 = await execute_tool(user.user_id, "write_file", {"path": test_file, "content": test_content})
    results.append({"step": "write_file", "label": "Écrire un fichier", "ok": bool(r2.get("ok")), "result": _shrink_for_ui(r2)})

    # 3. read_file (verify content)
    r3 = await execute_tool(user.user_id, "read_file", {"path": test_file})
    results.append({
        "step": "read_file",
        "label": "Lire le fichier (vérif round-trip)",
        "ok": bool(r3.get("ok")) and r3.get("content", "").strip() == test_content,
        "result": _shrink_for_ui(r3),
    })

    # 4. list_dir
    r4 = await execute_tool(user.user_id, "list_dir", {"path": "~"})
    results.append({"step": "list_dir", "label": "Lister le home", "ok": bool(r4.get("ok")), "result": _shrink_for_ui(r4)})

    # 5. edit_file round-trip
    r5 = await execute_tool(user.user_id, "edit_file", {
        "path": test_file,
        "old_string": test_content,
        "new_string": test_content + "-edited",
    })
    r5b = await execute_tool(user.user_id, "read_file", {"path": test_file})
    results.append({
        "step": "edit_file",
        "label": "Modifier un fichier (edit_file)",
        "ok": bool(r5.get("ok")) and r5b.get("content", "").strip().endswith("-edited"),
        "result": _shrink_for_ui(r5),
    })

    # 6. grep
    r6 = await execute_tool(user.user_id, "grep", {"pattern": "selftest", "path": "~/.emo"})
    results.append({
        "step": "grep",
        "label": "Recherche grep",
        "ok": bool(r6.get("ok")) and len(r6.get("matches") or []) > 0,
        "result": _shrink_for_ui(r6),
    })

    # cleanup
    await execute_tool(user.user_id, "delete_path", {"path": test_file})

    all_ok = all(s["ok"] for s in results)
    return {"ok": all_ok, "steps": results}


# ============================ HEALTH ============================ #

@api.get("/ping")
async def ping():
    return {
        "ok": True,
        "google": google_auth.is_configured(),
        "oauth_connections": {
            p: conn_accounts.is_provider_configured(p) for p in conn_accounts.PROVIDER_IDS
        },
        "service": "emo-online",
        "build": "2026-06-27a",
    }


@api.get("/health")
async def health_check():
    from llm_health import _probe_cache, _PROBE_TTL_SEC
    llm = await providers_status()
    now = __import__("time").monotonic()
    live = {}
    for name in llm:
        row = _probe_cache.get(name)
        if row:
            ok, ts, detail = row
            live[name] = ok and (now - ts) <= _PROBE_TTL_SEC
        else:
            live[name] = llm[name]
    working = [k for k, v in live.items() if v]
    return {
        "status": "ok",
        "mongodb": True,
        "llm_providers": llm,
        "llm_providers_live": live,
        "llm_ready": len(working) > 0,
        "google_oauth": google_auth.has_client_id(),
    }


@api.get("/")
async def root():
    return {"service": "emo", "status": "ok"}


app.include_router(api)


# --- Frontend statique (mode app installee / production) ---
FRONTEND_BUILD = ROOT_DIR.parent / "frontend" / "build"
_serve_frontend = os.environ.get("EMO_SERVE_FRONTEND", "auto").lower()
if _serve_frontend == "auto":
    SERVE_FRONTEND = (FRONTEND_BUILD / "index.html").is_file()
else:
    SERVE_FRONTEND = _serve_frontend in ("1", "true", "yes", "on")

if not SERVE_FRONTEND:
    @app.get("/")
    async def hf_space_root():
        return {"service": "emo", "status": "ok", "ping": "/api/ping"}

if SERVE_FRONTEND:
    from starlette.staticfiles import StaticFiles

    @app.get("/")
    async def spa_index():
        return FileResponse(FRONTEND_BUILD / "index.html")

    @app.get("/{full_path:path}")
    async def spa_files(full_path: str):
        if full_path.startswith("api") or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        target = (FRONTEND_BUILD / full_path).resolve()
        try:
            target.relative_to(FRONTEND_BUILD.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Not found")
        if target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_BUILD / "index.html")


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
