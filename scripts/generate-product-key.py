#!/usr/bin/env python3
"""Génère des clés produit commerciales (admin)."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "emo" / "backend"))
load_dotenv(ROOT / "emo" / "backend" / ".env", override=True)

from product_keys import create_product_keys  # noqa: E402


async def main():
    p = argparse.ArgumentParser(description="Génère des clés produit Émo Online")
    p.add_argument("--tier", default="ultra", choices=["basic", "premium", "ultra"])
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--uses", type=int, default=1, help="Activations max par clé")
    p.add_argument("--note", default="")
    args = p.parse_args()

    mongo = os.environ.get("MONGO_URL", "").strip()
    if not mongo:
        print("MONGO_URL manquant", file=sys.stderr)
        sys.exit(1)
    db = AsyncIOMotorClient(mongo)[os.environ.get("DB_NAME", "emo")]

    keys = await create_product_keys(
        db, tier=args.tier, count=args.count, max_uses=args.uses, note=args.note,
    )
    print(f"\n=== {len(keys)} clé(s) {args.tier.upper()} générée(s) ===\n")
    for k in keys:
        print(k)
    print("\nDonne une clé par client — accès illimité à vie.\n")


if __name__ == "__main__":
    asyncio.run(main())
