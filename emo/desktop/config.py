"""Chargement / sauvegarde de config/api_keys.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).resolve().parent / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

DEFAULT_BACKEND_BASE = "https://xroxx-emo-online-api.hf.space"

DEFAULT_CONFIG: dict[str, Any] = {
    "gemini_api_key": "",
    "openai_api_key": "",
    "backend_url": DEFAULT_BACKEND_BASE,
    "agent_token": "",
    "session_token": "",
    "user_email": "",
    "user_name": "",
    "conversation_id": "",
    "dashboard_port": 8000,
    "dashboard_pair_code": "",
    "site_url": "https://xeroxytb.com",
    "language": "fr",
    "gemini_live_model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
    "agent_folder": "",
    "camera_index": 0,
    "codegen_api_key": "",
    "codegen_provider": "ollama",
    "codegen_model": "llama3.2",
    "fallback_url": "http://localhost:11434",
    "os_system": "Windows",
}


def backend_base(url: str | None = None) -> str:
    """Base hôte sans suffixe /api (pour emo-agent long-poll)."""
    raw = (url or load_config().get("backend_url") or DEFAULT_BACKEND_BASE).strip().rstrip("/")
    if raw.endswith("/api"):
        return raw[:-4]
    return raw or DEFAULT_BACKEND_BASE


def backend_api(url: str | None = None) -> str:
    """URL API avec suffixe /api (pour httpx desktop → chat, auth)."""
    return f"{backend_base(url)}/api"


def _migrate_stale_backend(url: str) -> str:
    """Remplace les anciennes URLs locales par le cloud Emo Online."""
    u = (url or "").strip().rstrip("/")
    stale = (
        "http://127.0.0.1:8010",
        "http://localhost:8010",
        "http://127.0.0.1:8010/api",
        "http://localhost:8010/api",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
        "http://127.0.0.1:8001/api",
        "http://localhost:8001/api",
    )
    if u in stale:
        return DEFAULT_BACKEND_BASE
    return url


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        migrated = _migrate_stale_backend(str(merged.get("backend_url") or ""))
        if migrated != merged.get("backend_url"):
            merged["backend_url"] = migrated
            try:
                save_config(merged)
            except OSError:
                pass
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    CONFIG_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")


def get_key(name: str, default: str = "") -> str:
    return str(load_config().get(name) or default)
