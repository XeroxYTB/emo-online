#!/usr/bin/env python3
"""
Boucle autonome de test des capacités Émo (think/todo/plan + exécution agent).

Usage:
  py -3.11 scripts/emo_capability_loop.py
  py -3.11 scripts/emo_capability_loop.py --project task_platform --round 2
  py -3.11 scripts/emo_capability_loop.py --fix-report-only

Écrit les rapports dans scripts/capability_runs/<run_id>/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "emo" / "backend"))
try:
    import ssl_fix  # noqa: F401
except ImportError:
    pass

CONFIG_PATH = ROOT / "scripts" / "emo_capability_projects.json"
RUNS_DIR = ROOT / "scripts" / "capability_runs"


def _load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def login(client: httpx.Client, base: str, email: str, password: str) -> str:
    r = client.post(f"{base}/api/auth/login", json={"email": email, "password": password}, timeout=120)
    r.raise_for_status()
    data = r.json()
    token = data.get("session_token") or client.cookies.get("session_token")
    if not token:
        # Bearer from body if API returns it
        token = data.get("token")
    if not token:
        raise RuntimeError("Login OK but no session token")
    return token


def agent_status(client: httpx.Client, base: str, token: str) -> dict:
    r = client.get(
        f"{base}/api/agent/status",
        headers={"Authorization": f"Bearer {token}", "X-Emo-Session": token},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    return {"online": False, "error": r.text[:200]}


def create_conversation(client: httpx.Client, base: str, token: str, title: str) -> str:
    r = client.post(
        f"{base}/api/conversations",
        json={"title": title[:80], "mode": "tech"},
        headers={"Authorization": f"Bearer {token}", "X-Emo-Session": token},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["conversation_id"]


def stream_chat(
    client: httpx.Client,
    base: str,
    token: str,
    *,
    conversation_id: str,
    content: str,
    project_path: str,
    timeout_sec: int,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Emo-Session": token,
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    body = {
        "conversation_id": conversation_id,
        "content": content,
        "mode": "tech",
        "model_preference": "auto",
        "use_agent_tools": True,
        "agent_project_path": project_path,
    }
    metrics: dict[str, Any] = {
        "events": [],
        "tools": [],
        "thinks": [],
        "todos": [],
        "errors": [],
        "gates": [],
        "done": False,
        "assistant_preview": "",
    }
    start = time.time()
    with client.stream(
        "POST",
        f"{base}/api/chat/stream",
        json=body,
        headers=headers,
        timeout=httpx.Timeout(timeout_sec, connect=120),
    ) as resp:
        if resp.status_code != 200:
            metrics["errors"].append(f"HTTP {resp.status_code}: {resp.read().decode()[:500]}")
            return metrics
        buf = ""
        for chunk in resp.iter_text():
            if time.time() - start > timeout_sec:
                metrics["errors"].append("stream_timeout")
                break
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                for line in block.split("\n"):
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        evt = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    metrics["events"].append(evt.get("type"))
                    t = evt.get("type")
                    if t == "delta":
                        metrics["assistant_preview"] += evt.get("content") or ""
                    elif t == "tool_result":
                        tool = {
                            "name": evt.get("name"),
                            "ok": evt.get("result", {}).get("ok"),
                            "error": evt.get("result", {}).get("error"),
                        }
                        metrics["tools"].append(tool)
                        res = evt.get("result") or {}
                        if res.get("planning_gate") or res.get("think_gate"):
                            metrics["gates"].append({"tool": evt.get("name"), **res})
                        if res.get("ok") is False:
                            metrics["errors"].append(f"{evt.get('name')}: {res.get('error', '')[:200]}")
                    elif t == "think":
                        metrics["thinks"].append(evt)
                    elif t == "todo_update":
                        metrics["todos"].append(evt)
                    elif t == "error":
                        metrics["errors"].append(evt.get("content", "error"))
                    elif t == "done":
                        metrics["done"] = True
                        metrics["message_id"] = evt.get("message_id")
    metrics["assistant_preview"] = metrics["assistant_preview"][:4000]
    metrics["elapsed_sec"] = round(time.time() - start, 1)
    return metrics


def score_project(metrics: dict, criteria: dict, project_path: Path, agent_online: bool) -> dict:
    thinks = len(metrics.get("thinks") or [])
    tools_ok = sum(1 for t in metrics.get("tools") or [] if t.get("ok") is not False)
    tools_fail = sum(1 for t in metrics.get("tools") or [] if t.get("ok") is False)
    todo_events = metrics.get("todos") or []
    max_todos = max((len(e.get("todos") or []) for e in todo_events), default=0)
    finalized = any(e.get("planning_complete") for e in todo_events)
    set_plan = any(e.get("action") == "set_plan" for e in todo_events)

    points = 0
    max_pts = 100
    notes: list[str] = []

    if thinks >= criteria.get("min_thinks", 2):
        points += 20
    else:
        notes.append(f"Pas assez de emo_think ({thinks}/{criteria.get('min_thinks', 2)})")

    if max_todos >= criteria.get("min_todos_set", 5):
        points += 20
    else:
        notes.append(f"Todo plan insuffisant ({max_todos} tâches)")

    if not criteria.get("require_finalize_plan") or finalized:
        points += 15
    else:
        notes.append("finalize_plan jamais appelé")

    if set_plan:
        points += 10
    else:
        notes.append("set_plan jamais appelé")

    if tools_ok >= criteria.get("min_successful_tools", 8):
        points += 15
    else:
        notes.append(f"Peu d'outils OK ({tools_ok})")

    if metrics.get("done"):
        points += 10
    else:
        notes.append("Stream non terminé (done absent)")

    if not metrics.get("errors"):
        points += 10
    else:
        notes.append(f"{len(metrics['errors'])} erreur(s) tool/stream")

    files_found: list[str] = []
    if project_path.is_dir():
        for p in project_path.rglob("*"):
            if p.is_file():
                rel = p.relative_to(project_path).as_posix()
                files_found.append(rel)
    expected = criteria.get("expected_files_any") or []
    if expected:
        hit = any(
            any(rel.endswith(ex) or ex in rel for rel in files_found)
            for ex in expected
        )
        if hit:
            points += 10
        elif agent_online:
            notes.append(f"Fichiers attendus absents: {expected}")
        else:
            notes.append("Agent offline — fichiers non vérifiables (+0)")
    else:
        points += 10

    gate_after_finalize = finalized and any(
        g.get("planning_gate") for g in metrics.get("gates") or []
    )
    if criteria.get("require_no_planning_gate_after_finalize") and gate_after_finalize:
        points -= 10
        notes.append("Planning gate encore actif après finalize")

    return {
        "score": max(0, min(max_pts, points)),
        "notes": notes,
        "thinks": thinks,
        "tools_ok": tools_ok,
        "tools_fail": tools_fail,
        "max_todos": max_todos,
        "finalized": finalized,
        "files_count": len(files_found),
        "files_sample": files_found[:25],
    }


def follow_up_message(score: dict, round_idx: int) -> str:
    notes = score.get("notes") or []
    if round_idx == 1:
        return (
            "Continue le projet. Reprends PROJECT.md et la todo list. "
            "emo_think avant chaque write_file/exec_shell. Complete les tâches restantes."
        )
    issues = "; ".join(notes[:5]) if notes else "qualité insuffisante"
    return (
        f"Round {round_idx}: corrige ces problèmes — {issues}. "
        "Reprends le plan, mets à jour emo_todo, exécute sans skip think."
    )


def run_project(
    cfg: dict,
    project: dict,
    run_dir: Path,
    *,
    max_rounds: int,
    timeout_sec: int,
    min_score: int,
) -> dict:
    defaults = cfg["defaults"]
    base = defaults["backend_url"].rstrip("/")
    email = defaults["email"]
    password = defaults["password"]
    root = Path(defaults["project_root"])
    project_path = root / project["folder"]
    project_path.mkdir(parents=True, exist_ok=True)

    out: dict[str, Any] = {
        "project_id": project["id"],
        "name": project["name"],
        "project_path": str(project_path),
        "rounds": [],
        "passed": False,
    }

    with httpx.Client(follow_redirects=True) as client:
        token = login(client, base, email, password)
        client.headers.update({"Authorization": f"Bearer {token}", "X-Emo-Session": token})
        ag = agent_status(client, base, token)
        out["agent_online"] = bool(ag.get("online"))

        conv_id = create_conversation(client, base, token, f"[TEST] {project['name']}")
        out["conversation_id"] = conv_id

        content = project["prompt"]
        for rnd in range(1, max_rounds + 1):
            print(f"\n=== {project['id']} round {rnd}/{max_rounds} ===", flush=True)
            metrics = stream_chat(
                client, base, token,
                conversation_id=conv_id,
                content=content,
                project_path=str(project_path),
                timeout_sec=timeout_sec,
            )
            score = score_project(metrics, project.get("criteria", {}), project_path, out["agent_online"])
            round_doc = {
                "round": rnd,
                "prompt": content[:500],
                "metrics_summary": {
                    "elapsed_sec": metrics.get("elapsed_sec"),
                    "done": metrics.get("done"),
                    "tools": len(metrics.get("tools") or []),
                    "thinks": len(metrics.get("thinks") or []),
                    "errors": metrics.get("errors")[:10],
                },
                "score": score,
            }
            out["rounds"].append(round_doc)
            (run_dir / f"{project['id']}_round{rnd}.json").write_text(
                json.dumps({"metrics": metrics, "score": score}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Score: {score['score']}/100 — {score.get('notes')}", flush=True)
            if score["score"] >= min_score:
                out["passed"] = True
                out["final_score"] = score["score"]
                break
            content = follow_up_message(score, rnd)

    return out


def suggest_code_fixes(results: list[dict]) -> list[str]:
    """Heuristiques pour corrections Émo si scores bas."""
    fixes: list[str] = []
    for r in results:
        if r.get("passed"):
            continue
        for rnd in r.get("rounds") or []:
            sc = rnd.get("score") or {}
            for note in sc.get("notes") or []:
                if "emo_think" in note:
                    fixes.append("Renforcer prompt AGENT_COGNITION + gate think")
                if "finalize_plan" in note:
                    fixes.append("Auto-inject set_plan skeleton on mega project start")
                if "Agent offline" in note:
                    fixes.append("WARN: agent local requis — boucle ne peut pas valider fichiers")
                if "Stream non terminé" in note:
                    fixes.append("Augmenter timeout frontend ou max_agent_rounds backend")
    return list(dict.fromkeys(fixes))


def main() -> int:
    parser = argparse.ArgumentParser(description="Boucle test capacités Émo")
    parser.add_argument("--project", help="ID projet (sinon tous)")
    parser.add_argument("--round", type=int, default=0, help="Max rounds override")
    parser.add_argument("--fix-report-only", action="store_true")
    args = parser.parse_args()

    cfg = _load_config()
    defaults = cfg["defaults"]
    run_id = _run_id()
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    projects = cfg["projects"]
    if args.project:
        projects = [p for p in projects if p["id"] == args.project]
        if not projects:
            print(f"Projet inconnu: {args.project}", file=sys.stderr)
            return 1

    max_rounds = args.round or defaults["max_rounds_per_project"]
    results: list[dict] = []

    if not args.fix_report_only:
        for proj in projects:
            try:
                results.append(
                    run_project(
                        cfg, proj, run_dir,
                        max_rounds=max_rounds,
                        timeout_sec=defaults["stream_timeout_sec"],
                        min_score=defaults["min_score_to_pass"],
                    )
                )
            except Exception as e:
                results.append({
                    "project_id": proj["id"],
                    "passed": False,
                    "fatal_error": str(e),
                })

    report = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "suggested_fixes": suggest_code_fixes(results),
        "passed_count": sum(1 for r in results if r.get("passed")),
        "total": len(projects) if not args.fix_report_only else 0,
    }
    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRapport: {report_path}", flush=True)
    print(f"Passés: {report['passed_count']}/{len(projects)}", flush=True)
    if report["suggested_fixes"]:
        print("Fixes suggérés:", report["suggested_fixes"], flush=True)
    return 0 if report["passed_count"] == len(projects) else 1


if __name__ == "__main__":
    raise SystemExit(main())
