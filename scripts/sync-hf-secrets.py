#!/usr/bin/env python3
"""Load backend/.env and sync HF Space secrets + variables."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "emo" / "backend" / ".env", override=True)

if not os.environ.get("HF_TOKEN", "").strip():
    print("HF_TOKEN manquant", file=sys.stderr)
    sys.exit(1)

script = ROOT / "scripts" / "setup-hf-space.py"
raise SystemExit(subprocess.call([sys.executable, str(script)], env=os.environ.copy()))
