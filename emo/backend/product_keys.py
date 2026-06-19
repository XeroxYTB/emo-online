"""Clés produit commerciales — accès illimité pour ventes (lifetime, multi-tiers)."""
from __future__ import annotations

import hashlib
import os
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

TIER_ALIASES = {"basic": "basic", "premium": "premium", "ultra": "ultra", "pro": "premium", "max": "ultra"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.strip().upper().encode()).hexdigest()


def normalize_key(raw: str) -> str:
    return raw.strip().upper().replace(" ", "")


def generate_key(tier: str = "ultra", prefix: str = "EMO") -> str:
    tier = TIER_ALIASES.get(tier.lower(), "ultra")
    alphabet = string.ascii_uppercase + string.digits
    blocks = "".join(secrets.choice(alphabet) for _ in range(4))
    blocks2 = "".join(secrets.choice(alphabet) for _ in range(4))
    blocks3 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{prefix}-{tier.upper()}-{blocks}-{blocks2}-{blocks3}"


def parse_env_product_keys() -> list[dict]:
    """EMO_PRODUCT_KEYS=ultra:EMO-ULTRA-AAAA-BBBB-CCCC,basic:EMO-BASIC-..."""
    raw = os.environ.get("EMO_PRODUCT_KEYS", "").strip()
    if not raw:
        return []
    out = []
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        tier, key = part.split(":", 1)
        tier = TIER_ALIASES.get(tier.strip().lower(), "ultra")
        key = normalize_key(key)
        if key:
            out.append({"tier": tier, "key": key, "max_uses": 1, "note": "env_seed"})
    return out


async def ensure_product_keys_seeded(db: AsyncIOMotorDatabase) -> int:
    """Importe EMO_PRODUCT_KEYS dans MongoDB au démarrage (idempotent)."""
    seeded = 0
    for item in parse_env_product_keys():
        key = item["key"]
        h = hash_key(key)
        exists = await db.product_keys.find_one({"key_hash": h}, {"_id": 1})
        if exists:
            continue
        await db.product_keys.insert_one({
            "key_hash": h,
            "key_prefix": key[:16],
            "tier": item["tier"],
            "lifetime": True,
            "max_uses": item.get("max_uses", 1),
            "uses": 0,
            "active": True,
            "note": item.get("note", "env_seed"),
            "created_at": _now(),
            "redeemed_by": [],
        })
        seeded += 1
    return seeded


async def create_product_keys(
    db: AsyncIOMotorDatabase,
    *,
    tier: str = "ultra",
    count: int = 1,
    max_uses: int = 1,
    note: str = "",
) -> list[str]:
    tier = TIER_ALIASES.get(tier.lower(), "ultra")
    count = max(1, min(int(count), 50))
    keys = []
    for _ in range(count):
        raw = generate_key(tier)
        await db.product_keys.insert_one({
            "key_hash": hash_key(raw),
            "key_prefix": raw[:20],
            "tier": tier,
            "lifetime": True,
            "max_uses": max(1, int(max_uses)),
            "uses": 0,
            "active": True,
            "note": note or "",
            "created_at": _now(),
            "redeemed_by": [],
        })
        keys.append(raw)
    return keys


async def redeem_product_key(
    db: AsyncIOMotorDatabase,
    *,
    raw_key: str,
    user_id: str,
    email: str,
) -> dict:
    key = normalize_key(raw_key)
    if len(key) < 12:
        raise ValueError("Clé invalide")
    h = hash_key(key)
    doc = await db.product_keys.find_one({"key_hash": h, "active": True}, {"_id": 0})
    if not doc:
        raise ValueError("Clé inconnue ou désactivée")
    uses = int(doc.get("uses", 0))
    max_uses = int(doc.get("max_uses", 1))
    if uses >= max_uses:
        raise ValueError("Cette clé a déjà été utilisée")

    tier = doc.get("tier", "ultra")
    now = _now()
    await db.product_keys.update_one(
        {"key_hash": h},
        {
            "$inc": {"uses": 1},
            "$push": {"redeemed_by": {"user_id": user_id, "email": email, "at": now}},
        },
    )
    license_set = {
        "paid": True,
        "status": "active",
        "tier": tier,
        "source": "product_key",
        "lifetime": True,
        "interval": "lifetime",
        "valid_until": None,
        "paid_at": now,
        "product_key_prefix": doc.get("key_prefix", key[:16]),
        "subscription_status": "active",
        "daily_count": 0,
        "daily_day": now[:10],
    }
    await db.licenses.update_one({"user_id": user_id}, {"$set": license_set}, upsert=True)
    return {"tier": tier, "lifetime": True, "source": "product_key"}


def is_commercial_license(lic: dict) -> bool:
    """Accès vente / clé produit / abonnement payant actif."""
    if not lic:
        return False
    if lic.get("source") == "product_key" and lic.get("lifetime"):
        return True
    tier = lic.get("tier")
    if tier in ("basic", "premium", "ultra") and lic.get("paid"):
        return True
    return False
