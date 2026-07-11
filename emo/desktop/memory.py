"""Mémoire persistante long_term.json."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
MEMORY_FILE = DATA_DIR / "long_term.json"


def _default_memory() -> dict[str, Any]:
    return {
        "preferences": {},
        "facts": [],
        "journal": [],
        "updated_at": None,
    }


def load_memory() -> dict[str, Any]:
    if not MEMORY_FILE.exists():
        return _default_memory()
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        base = _default_memory()
        base.update(data)
        return base
    except (json.JSONDecodeError, OSError):
        return _default_memory()


def save_memory(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def set_preference(key: str, value: Any) -> None:
    mem = load_memory()
    mem.setdefault("preferences", {})[key] = value
    save_memory(mem)


def get_preference(key: str, default: Any = None) -> Any:
    return load_memory().get("preferences", {}).get(key, default)


def add_fact(text: str) -> None:
    mem = load_memory()
    mem.setdefault("facts", []).append({
        "text": text,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    if len(mem["facts"]) > 200:
        mem["facts"] = mem["facts"][-200:]
    save_memory(mem)


def append_journal(entry: str) -> None:
    mem = load_memory()
    mem.setdefault("journal", []).append({
        "text": entry,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    if len(mem["journal"]) > 500:
        mem["journal"] = mem["journal"][-500:]
    save_memory(mem)
