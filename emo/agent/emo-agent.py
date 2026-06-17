#!/usr/bin/env python3
"""
emo-agent — Local execution agent for Émo (HTTP long-polling).

Hugo runs this on his PC. It long-polls the Émo backend for tool requests
(exec_shell, read_file, write_file, list_dir), executes them locally, and
posts results back. No WebSocket required (more resilient through proxies).

USAGE:
    python3 emo-agent.py --token <YOUR_AGENT_TOKEN>

Env vars:
    EMO_AGENT_TOKEN
    EMO_BACKEND_URL (default: http://127.0.0.1:8010 or your cloud URL)

DEPS:
    pip install httpx

SECURITY:
    The agent runs ARBITRARY shell commands. Keep your token secret. Rotate it
    from the Émo UI if it leaks. The agent has the same privileges as the user
    that started it.
"""
import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("[emo-agent] Missing dependency. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)


DEFAULT_BACKEND = os.environ.get("EMO_BACKEND_URL", "http://127.0.0.1:8010")


# ----------------------------- TOOLS ----------------------------- #

async def tool_exec_shell(args: dict) -> dict:
    cmd = args.get("cmd") or ""
    cwd = args.get("cwd") or None
    timeout = int(args.get("timeout") or 60)
    if not cmd:
        return {"ok": False, "error": "cmd missing"}
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": False, "error": f"timeout after {timeout}s", "exit_code": -1}
        return {
            "ok": True,
            "exit_code": proc.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_read_file(args: dict) -> dict:
    path = args.get("path")
    if not path:
        return {"ok": False, "error": "path missing"}
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return {"ok": False, "error": "file not found"}
        if p.stat().st_size > 5 * 1024 * 1024:
            return {"ok": False, "error": "file too large (>5MB) — use offset/limit or grep"}
        content = p.read_text(errors="replace")
        offset = int(args.get("offset") or 1)
        limit = int(args.get("limit") or 0)
        if offset > 1 or limit > 0:
            lines = content.splitlines(keepends=True)
            start = max(0, offset - 1)
            end = len(lines) if limit <= 0 else min(len(lines), start + limit)
            numbered = []
            for i, ln in enumerate(lines[start:end], start=start + 1):
                numbered.append(f"{i:6d}|{ln.rstrip(chr(10))}")
            content = "\n".join(numbered) + ("\n" if numbered else "")
        return {"ok": True, "content": content, "path": str(p.resolve()), "offset": offset, "limit": limit}
    except Exception as e:
        err = str(e)
        if "aswMonFltProxy" in err or "Permission denied" in err:
            return {"ok": False, "error": "Avast bloque l acces au fichier. Ajoute une exception pour Emo Online dans Avast."}
        return {"ok": False, "error": err}


async def tool_write_file(args: dict) -> dict:
    path = args.get("path")
    content = args.get("content")
    if not path or content is None:
        return {"ok": False, "error": "path and content required"}
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"ok": True, "path": str(p.resolve()), "bytes": len(content.encode())}
    except Exception as e:
        err = str(e)
        if "aswMonFltProxy" in err or "Permission denied" in err:
            return {"ok": False, "error": "Avast bloque l acces au fichier. Ajoute une exception pour Emo Online dans Avast."}
        return {"ok": False, "error": err}


async def tool_list_dir(args: dict) -> dict:
    path = args.get("path") or "."
    depth = int(args.get("depth") or 1)
    depth = min(max(depth, 1), 4)
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return {"ok": False, "error": "path not found"}
        if not p.is_dir():
            return {"ok": False, "error": "not a directory"}
        root = p.resolve()
        if depth <= 1:
            files, dirs = [], []
            for entry in sorted(p.iterdir()):
                if entry.name.startswith("."):
                    continue
                (dirs if entry.is_dir() else files).append(entry.name)
            return {"ok": True, "path": str(root), "files": files, "dirs": dirs}
        entries = []
        skip_dirs = {".git", "node_modules", "__pycache__", "vendor"}

        def walk(d: Path, lvl: int):
            if lvl > depth or len(entries) >= 500:
                return
            try:
                items = sorted(d.iterdir())
            except OSError:
                return
            for entry in items:
                if entry.name.startswith("."):
                    continue
                rel = entry.relative_to(root).as_posix()
                entries.append({"path": rel, "is_dir": entry.is_dir()})
                if entry.is_dir() and lvl < depth and entry.name not in skip_dirs and len(entries) < 500:
                    walk(entry, lvl + 1)

        walk(p, 1)
        return {"ok": True, "path": str(root), "entries": entries, "truncated": len(entries) >= 500}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _is_binary_sample(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    return any(b < 9 or (13 < b < 32) for b in data)


async def tool_grep(args: dict) -> dict:
    pattern = args.get("pattern") or ""
    if not pattern:
        return {"ok": False, "error": "pattern missing"}
    root = Path(args.get("path") or ".").expanduser()
    glob_pat = args.get("glob") or "*"
    max_results = min(int(args.get("max_results") or 100), 200)
    ignore_case = bool(args.get("ignore_case"))
    needle = pattern.lower() if ignore_case else pattern
    skip_dirs = {".git", "node_modules", "__pycache__", "vendor"}
    matches = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in skip_dirs]
        for fname in filenames:
            if len(matches) >= max_results:
                break
            if glob_pat != "*" and not Path(fname).match(glob_pat):
                continue
            fp = Path(dirpath) / fname
            try:
                if fp.stat().st_size > 2 * 1024 * 1024:
                    continue
                head = fp.read_bytes()[:512]
                if _is_binary_sample(head):
                    continue
                with fp.open("r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        hay = line.lower() if ignore_case else line
                        if needle in hay:
                            matches.append({"file": str(fp), "line": i, "text": line[:300]})
                            if len(matches) >= max_results:
                                break
            except OSError:
                continue
        if len(matches) >= max_results:
            break
    return {"ok": True, "pattern": pattern, "matches": matches, "truncated": len(matches) >= max_results}


async def tool_edit_file(args: dict) -> dict:
    path = args.get("path")
    old = args.get("old_string")
    new = args.get("new_string")
    if not path or old is None or new is None:
        return {"ok": False, "error": "path, old_string, new_string required"}
    try:
        p = Path(path).expanduser()
        content = p.read_text(errors="replace")
        count = content.count(old)
        if count == 0:
            return {"ok": False, "error": "old_string not found"}
        replace_all = bool(args.get("replace_all"))
        if not replace_all and count > 1:
            return {"ok": False, "error": f"old_string found {count} times — use replace_all or be more specific"}
        if replace_all:
            updated = content.replace(old, new)
            replaced = count
        else:
            updated = content.replace(old, new, 1)
            replaced = 1
        p.write_text(updated)
        return {"ok": True, "path": str(p.resolve()), "replacements": replaced}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_delete_path(args: dict) -> dict:
    path = args.get("path")
    if not path:
        return {"ok": False, "error": "path missing"}
    try:
        p = Path(path).expanduser()
        if p.is_dir():
            import shutil
            shutil.rmtree(p)
        else:
            p.unlink(missing_ok=False)
        return {"ok": True, "deleted": str(p)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_move_path(args: dict) -> dict:
    src = args.get("from")
    dst = args.get("to")
    if not src or not dst:
        return {"ok": False, "error": "from and to required"}
    try:
        f = Path(src).expanduser()
        t = Path(dst).expanduser()
        t.parent.mkdir(parents=True, exist_ok=True)
        f.rename(t)
        return {"ok": True, "from": str(f), "to": str(t.resolve())}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_find_files(args: dict) -> dict:
    pattern = args.get("pattern") or ""
    if not pattern:
        return {"ok": False, "error": "pattern missing"}
    root = Path(args.get("path") or ".").expanduser()
    max_results = min(int(args.get("max_results") or 200), 500)
    skip_dirs = {".git", "node_modules"}
    found = []
    has_glob = "*" in pattern

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in skip_dirs]
        for fname in filenames:
            if len(found) >= max_results:
                break
            fp = Path(dirpath) / fname
            if has_glob:
                if not Path(fname).match(pattern):
                    continue
            elif pattern.lower() not in str(fp).lower():
                continue
            found.append(str(fp))
        if len(found) >= max_results:
            break
    return {"ok": True, "pattern": pattern, "files": found, "truncated": len(found) >= max_results}


async def tool_codebase_search(args: dict) -> dict:
    query = (args.get("query") or args.get("pattern") or "").strip()
    if not query:
        return {"ok": False, "error": "query missing"}
    path = args.get("path") or "."
    dirs = args.get("target_directories")
    if isinstance(dirs, list) and dirs:
        path = dirs[0]
    return await tool_grep({
        "pattern": query,
        "path": path,
        "ignore_case": True,
        "max_results": int(args.get("max_results") or 80),
    })


TOOLS = {
    "exec_shell": tool_exec_shell,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "list_dir": tool_list_dir,
    "grep": tool_grep,
    "edit_file": tool_edit_file,
    "delete_path": tool_delete_path,
    "move_path": tool_move_path,
    "find_files": tool_find_files,
    "codebase_search": tool_codebase_search,
    "run_terminal_cmd": tool_exec_shell,
    "run_terminal_command": tool_exec_shell,
    "bash": tool_exec_shell,
    "file_search": tool_find_files,
    "delete_file": tool_delete_path,
    "create_file": tool_write_file,
    "grep_search": tool_grep,
}


# ----------------------------- POLL LOOP ----------------------------- #

def _shrink(args: dict) -> str:
    s = json.dumps(args, ensure_ascii=False)
    return s if len(s) < 120 else s[:117] + "..."


def _summarize(result: dict) -> str:
    if not result.get("ok"):
        return f"ERROR: {result.get('error', '')[:120]}"
    if "exit_code" in result:
        return f"exit={result['exit_code']}, out={len(result.get('stdout', ''))}c"
    if "content" in result:
        return f"read {len(result['content'])} chars"
    if "matches" in result:
        return f"{len(result['matches'])} matches"
    if "entries" in result:
        return f"{len(result['entries'])} entries"
    if "replacements" in result:
        return f"{result['replacements']} edits"
    if "files" in result and isinstance(result["files"], list) and "dirs" not in result:
        return f"{len(result['files'])} files found"
    if "files" in result:
        return f"{len(result['files'])} files, {len(result.get('dirs', []))} dirs"
    if "deleted" in result:
        return "deleted"
    if "from" in result and "to" in result:
        return "moved"
    return "ok"


async def execute_and_post(client: httpx.AsyncClient, backend: str, token: str, req: dict):
    rid = req.get("id")
    tool = req.get("tool")
    args = req.get("args") or {}
    handler = TOOLS.get(tool)
    if handler is None:
        result = {"ok": False, "error": f"unknown tool: {tool}"}
    else:
        try:
            print(f"[emo-agent] → {tool}({_shrink(args)})")
            result = await handler(args)
            print(f"[emo-agent] ← {_summarize(result)}")
        except Exception as e:
            result = {"ok": False, "error": f"handler crashed: {e}"}
    try:
        await client.post(
            f"{backend}/api/agent/result",
            params={"token": token},
            json={"id": rid, "result": result},
            timeout=15,
        )
    except Exception as e:
        print(f"[emo-agent] ! failed to post result: {e}")


async def heartbeat_loop(client: httpx.AsyncClient, backend: str, token: str):
    while True:
        try:
            await client.post(f"{backend}/api/agent/heartbeat", params={"token": token}, timeout=10)
        except Exception:
            pass
        await asyncio.sleep(5)


async def run(token: str, backend: str):
    backend = backend.rstrip("/")
    print(f"[emo-agent] backend = {backend}")
    print("[emo-agent] starting… Ctrl+C to quit.")
    async with httpx.AsyncClient() as client:
        # First heartbeat to validate token & go online
        try:
            r = await client.post(f"{backend}/api/agent/heartbeat", params={"token": token}, timeout=10)
            if r.status_code != 200:
                print(f"[emo-agent] auth failed (HTTP {r.status_code}): {r.text}")
                return
        except Exception as e:
            print(f"[emo-agent] cannot reach backend: {e}")
            return
        print("[emo-agent] online. Émo can now pilot this machine.")

        asyncio.create_task(heartbeat_loop(client, backend, token))

        while True:
            try:
                r = await client.get(
                    f"{backend}/api/agent/poll",
                    params={"token": token},
                    timeout=35,
                )
                if r.status_code != 200:
                    print(f"[emo-agent] poll error {r.status_code}; retrying in 3s")
                    await asyncio.sleep(3)
                    continue
                data = r.json()
                if data.get("empty"):
                    continue  # re-poll immediately
                req = data.get("request") or {}
                asyncio.create_task(execute_and_post(client, backend, token, req))
            except httpx.ReadTimeout:
                continue
            except KeyboardInterrupt:
                print("\n[emo-agent] bye.")
                return
            except Exception as e:
                print(f"[emo-agent] poll exception: {e}; retrying in 3s")
                await asyncio.sleep(3)


def main():
    ap = argparse.ArgumentParser(description="Émo local agent")
    ap.add_argument("--token", default=os.environ.get("EMO_AGENT_TOKEN"))
    ap.add_argument("--backend", default=DEFAULT_BACKEND)
    args = ap.parse_args()
    if not args.token:
        print("[emo-agent] Token required. Use --token or EMO_AGENT_TOKEN env var.", file=sys.stderr)
        sys.exit(2)
    try:
        asyncio.run(run(args.token, args.backend))
    except KeyboardInterrupt:
        print("\n[emo-agent] bye.")


if __name__ == "__main__":
    main()
