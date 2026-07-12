"""Client HTTP vers Emo Online (auth, chat SSE, sync conversations)."""
from __future__ import annotations

import json
from typing import Any, Callable

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from emo.desktop.config import backend_api, load_config, save_config

DEFAULT_BACKEND = "https://xroxx-emo-online-api.hf.space/api"


def normalize_backend_url(url: str | None = None) -> str:
    """Retourne une base se terminant par /api (sans double suffixe)."""
    return backend_api(url) if url else backend_api()


def _auth_headers(session_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {session_token}",
        "X-Emo-Session": session_token,
    }


class CloudClient:
    """Accès API Emo Online pour le desktop."""

    def __init__(self, on_log: Callable[[str], None] | None = None):
        self.on_log = on_log

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    @property
    def base(self) -> str:
        return normalize_backend_url()

    def _token(self) -> str:
        return (load_config().get("session_token") or "").strip()

    async def ping(self) -> bool:
        if httpx is None:
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{self.base}/ping")
                return r.status_code == 200
        except Exception:
            return False

    async def login(self, email: str, password: str) -> dict[str, Any]:
        if httpx is None:
            return {"ok": False, "error": "httpx requis"}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{self.base}/auth/login",
                    json={"email": email.strip(), "password": password},
                )
                if r.status_code != 200:
                    detail = r.text[:200]
                    try:
                        detail = r.json().get("detail", detail)
                    except Exception:
                        pass
                    return {"ok": False, "error": str(detail)}
                data = r.json()
                cfg = load_config()
                cfg["session_token"] = data.get("session_token", "")
                cfg["user_email"] = data.get("email", email)
                cfg["user_name"] = data.get("name", "")
                save_config(cfg)
                self._log(f"Cloud: connecté en tant que {cfg['user_email']}")
                agent = await self.fetch_agent_token(cfg["session_token"])
                if agent.get("agent_token"):
                    cfg = load_config()
                    cfg["agent_token"] = agent["agent_token"]
                    save_config(cfg)
                    self._log("Cloud: token agent récupéré.")
                conv = await self.ensure_conversation(cfg["session_token"])
                if conv.get("conversation_id"):
                    cfg = load_config()
                    cfg["conversation_id"] = conv["conversation_id"]
                    save_config(cfg)
                return {"ok": True, **data, "agent_token": agent.get("agent_token")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def fetch_agent_token(self, session_token: str | None = None) -> dict[str, Any]:
        token = session_token or self._token()
        if not token or httpx is None:
            return {}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{self.base}/agent/token",
                    headers=_auth_headers(token),
                )
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return {}

    async def ensure_conversation(self, session_token: str | None = None) -> dict[str, Any]:
        token = session_token or self._token()
        if not token or httpx is None:
            return {}
        cfg = load_config()
        cid = (cfg.get("conversation_id") or "").strip()
        headers = _auth_headers(token)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if cid:
                    r = await client.get(f"{self.base}/conversations/{cid}/messages", headers=headers)
                    if r.status_code == 200:
                        return {"conversation_id": cid}
                r = await client.get(f"{self.base}/conversations", headers=headers)
                if r.status_code == 200:
                    convs = r.json()
                    for c in convs:
                        title = (c.get("title") or "").lower()
                        if "desktop" in title or "ém" in title:
                            return {"conversation_id": c.get("conversation_id")}
                    if convs:
                        return {"conversation_id": convs[0].get("conversation_id")}
                r = await client.post(
                    f"{self.base}/conversations",
                    headers=headers,
                    json={"title": "Émo Desktop", "mode": "tech"},
                )
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            self._log(f"Cloud: conversation — {e}")
        return {}

    async def chat(self, message: str) -> str:
        token = self._token()
        if not token:
            return (
                "Connectez-vous à Emo Online : Paramètres → email/mot de passe "
                "ou collez session_token + agent_token."
            )
        if httpx is None:
            return "httpx requis. pip install httpx"

        cfg = load_config()
        cid = (cfg.get("conversation_id") or "").strip()
        if not cid:
            conv = await self.ensure_conversation(token)
            cid = conv.get("conversation_id", "")
            if cid:
                cfg["conversation_id"] = cid
                save_config(cfg)
        if not cid:
            return "Impossible de créer une conversation cloud."

        headers = {
            **_auth_headers(token),
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }
        body = {
            "conversation_id": cid,
            "content": message,
            "mode": "tech",
            "use_agent_tools": False,
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{self.base}/chat/stream",
                    json=body,
                    headers=headers,
                ) as resp:
                    if resp.status_code == 401:
                        return "Session expirée — reconnectez-vous dans Paramètres."
                    if resp.status_code == 429:
                        return "Service cloud saturé (429). Réessayez dans quelques minutes."
                    if resp.status_code != 200:
                        text = (await resp.aread()).decode(errors="replace")[:300]
                        return f"Erreur cloud ({resp.status_code}): {text}"

                    parts: list[str] = []
                    buf = ""
                    async for chunk in resp.aiter_text():
                        buf += chunk
                        while "\n\n" in buf:
                            block, buf = buf.split("\n\n", 1)
                            for line in block.strip().split("\n"):
                                if not line.startswith("data:"):
                                    continue
                                payload = line[5:].strip()
                                if not payload:
                                    continue
                                try:
                                    evt = json.loads(payload)
                                except json.JSONDecodeError:
                                    continue
                                etype = evt.get("type")
                                if etype == "delta":
                                    parts.append(evt.get("content") or "")
                                elif etype == "done":
                                    return evt.get("content") or "".join(parts) or "…"
                                elif etype == "error":
                                    err = evt.get("content") or "Erreur cloud"
                                    return "".join(parts) or err
                    return "".join(parts) or "Pas de réponse du cloud."
        except Exception as e:
            return f"Impossible de joindre le cloud: {e}"

    async def pull_messages(self, limit: int = 30) -> list[dict[str, Any]]:
        token = self._token()
        cid = (load_config().get("conversation_id") or "").strip()
        if not token or not cid or httpx is None:
            return []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{self.base}/conversations/{cid}/messages",
                    headers=_auth_headers(token),
                )
                if r.status_code == 200:
                    msgs = r.json()
                    return msgs[-limit:] if isinstance(msgs, list) else []
        except Exception:
            pass
        return []

    async def sync_status(self) -> dict[str, Any]:
        token = self._token()
        cloud_ok = await self.ping() if token else False
        agent_tools_online = False
        desktop_online = False
        desktop_linked = False
        if token:
            await self.send_heartbeat()
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get(
                        f"{self.base}/agent/status",
                        headers=_auth_headers(token),
                    )
                    if r.status_code == 200:
                        st = r.json()
                        agent_tools_online = bool(st.get("online"))
                        desktop_online = bool(st.get("desktop_online"))
                        desktop_linked = bool(st.get("desktop_linked"))
            except Exception:
                pass
        return {
            "cloud_ok": cloud_ok,
            "logged_in": bool(token),
            "agent_online": agent_tools_online,
            "desktop_online": desktop_online,
            "desktop_linked": desktop_linked,
            "connected": desktop_online or agent_tools_online,
            "email": load_config().get("user_email", ""),
        }

    async def send_heartbeat(self) -> bool:
        token = self._token()
        if not token or httpx is None:
            return False
        import platform

        body = {
            "client": "emo-desktop",
            "os": platform.system(),
            "hostname": platform.node(),
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{self.base}/desktop/heartbeat",
                    json=body,
                    headers=_auth_headers(token),
                )
                return r.status_code == 200
        except Exception:
            return False

    async def poll_pair_claim(self, code: str) -> dict[str, Any]:
        """Récupère tokens après confirmation sur le site (une seule fois)."""
        code = (code or "").strip().upper()
        if not code or httpx is None:
            return {"ok": False, "pending": True}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{self.base}/desktop/pair/poll", params={"code": code})
                if r.status_code != 200:
                    return {"ok": False, "pending": True}
                data = r.json()
                if not data.get("ok"):
                    return data
                cfg = load_config()
                cfg["session_token"] = data.get("session_token", "")
                cfg["agent_token"] = data.get("agent_token", "")
                if data.get("email"):
                    cfg["user_email"] = data["email"]
                if data.get("name"):
                    cfg["user_name"] = data["name"]
                save_config(cfg)
                conv = await self.ensure_conversation(cfg["session_token"])
                if conv.get("conversation_id"):
                    cfg = load_config()
                    cfg["conversation_id"] = conv["conversation_id"]
                    save_config(cfg)
                self._log(f"Cloud: appairage site OK ({cfg.get('user_email', '')})")
                return data
        except Exception as e:
            return {"ok": False, "error": str(e)}
