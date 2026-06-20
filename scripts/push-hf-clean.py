#!/usr/bin/env python3
"""Push a clean tree to Hugging Face Space (sans binaires dans l'historique git)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {
    ".git", "login_test_artifacts", "scripts/login_test_output",
    "node_modules", "emo/frontend/node_modules", "emo/frontend/build",
    "__pycache__", ".pytest_cache", "emo/backend/.env",
}


def _load_hf_token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip()
    if token:
        return token
    env_path = ROOT / "emo" / "backend" / ".env"
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("HF_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def should_skip(rel: str) -> bool:
    parts = Path(rel).parts
    for ex in EXCLUDE:
        if ex in parts or rel.startswith(ex + "/") or rel == ex:
            return True
    if rel.endswith((".png", ".jpg", ".exe", ".dll", ".py")) and "login_browser" in rel:
        return True
    if rel.endswith((".png", ".jpg", ".exe", ".dll")) and "login_test" in rel:
        return True
    return False


def main() -> int:
    token = _load_hf_token()
    if not token:
        print("HF_TOKEN manquant", file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="emo-hf-"))
    try:
        for src in ROOT.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(ROOT).as_posix()
            if should_skip(rel):
                continue
            dest = tmp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        subprocess.run(["git", "init", "-b", "main"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.email", "emo@users.noreply.github.com"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.name", "Emo Online"], cwd=tmp, check=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
        subprocess.run(["git", "commit", "-m", "Deploy Emo API"], cwd=tmp, check=True)
        remote = f"https://Xroxx:{token}@huggingface.co/spaces/Xroxx/emo-online-api"
        subprocess.run(["git", "remote", "add", "space", remote], cwd=tmp, check=True)
        subprocess.run(["git", "push", "space", "main", "--force"], cwd=tmp, check=True)
        print("HF Space deploy OK")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
