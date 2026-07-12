"""Dashboard FastAPI — télécommande mobile port 8000."""
from __future__ import annotations

import asyncio
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, File, Request, UploadFile, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError:
    FastAPI = None  # type: ignore
    File = None  # type: ignore
    UploadFile = None  # type: ignore
    WebSocket = None  # type: ignore
    WebSocketDisconnect = None  # type: ignore
    uvicorn = None  # type: ignore

from emo.desktop.config import load_config, save_config

_log_subscribers: list[Any] = []
_command_handler: Any = None
_pair_handler: Any = None
_wake_handler: Any = None
_phone_audio_handler: Any = None
_live_session_ref: Any = None
_phone_audio_queue: asyncio.Queue | None = None
_pair_code: str = ""


def dashboard_local_url(port: int = 8000, path: str = "/pair") -> str:
    """URL affichée à l'utilisateur (127.0.0.1 — pas 0.0.0.0)."""
    return f"http://127.0.0.1:{port}{path}"


def site_link_url(code: str | None = None, port: int = 8000) -> str:
    """URL Emo Online pour confirmer l'appairage desktop."""
    cfg = load_config()
    site = (cfg.get("site_url") or "https://xeroxytb.com").rstrip("/")
    c = (code or _get_pair_code()).strip().upper()
    return f"{site}/link-desktop?code={c}&port={port}"


def set_command_handler(handler) -> None:
    global _command_handler
    _command_handler = handler


def set_pair_handler(handler) -> None:
    global _pair_handler
    _pair_handler = handler


def set_wake_handler(handler) -> None:
    global _wake_handler
    _wake_handler = handler


def set_live_session(session) -> None:
    """Lie la session Live pour le relais audio téléphone."""
    global _live_session_ref, _phone_audio_queue
    _live_session_ref = session
    if session is not None:
        if _phone_audio_queue is None:
            _phone_audio_queue = asyncio.Queue(maxsize=200)
        session.phone_audio_queue = _phone_audio_queue


def get_phone_audio_queue() -> asyncio.Queue:
    global _phone_audio_queue
    if _phone_audio_queue is None:
        _phone_audio_queue = asyncio.Queue(maxsize=200)
    return _phone_audio_queue


def set_phone_audio_handler(handler) -> None:
    global _phone_audio_handler
    _phone_audio_handler = handler


def _notify_paired(source: str) -> None:
    broadcast_log(f"[pair] Connecté via {source}")
    if _pair_handler:
        try:
            _pair_handler(source)
        except Exception:
            pass


async def _save_cloud_tokens(session_token: str, agent_token: str = "") -> dict[str, Any]:
    cfg = load_config()
    cfg["session_token"] = session_token
    if agent_token:
        cfg["agent_token"] = agent_token
    save_config(cfg)
    from emo.desktop.cloud_client import CloudClient

    client = CloudClient()
    conv = await client.ensure_conversation(session_token)
    if conv.get("conversation_id"):
        cfg = load_config()
        cfg["conversation_id"] = conv["conversation_id"]
        save_config(cfg)
    return conv


def _pair_html(info: dict[str, Any]) -> str:
    code = info.get("code", "")
    port = info.get("port", 8000)
    site_url = info.get("site_url", "https://xeroxytb.com")
    link = f"{site_url.rstrip('/')}/link-desktop?code={code}&port={port}"
    logged = info.get("logged_in")
    email = info.get("email") or ""
    status = f"Connecté : {email}" if logged else "En attente de confirmation sur le site"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Émo Desktop — Appairage</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; background: #010408; color: #c8ebf8; margin: 0; padding: 24px; }}
    .card {{ max-width: 420px; margin: 0 auto; background: rgba(0,18,30,.85); border: 1px solid rgba(0,180,220,.25);
      border-radius: 12px; padding: 24px; }}
    h1 {{ font-size: 1.25rem; color: #00d4e8; margin: 0 0 8px; }}
    p {{ font-size: 0.9rem; color: rgba(130,190,215,.85); line-height: 1.5; }}
    .code {{ font-family: Consolas, monospace; font-size: 1.5rem; letter-spacing: .2em; color: #e8d080;
      text-align: center; padding: 12px; border: 1px dashed rgba(184,160,80,.4); border-radius: 8px; margin: 12px 0; }}
    .btn {{ display: block; text-align: center; margin-top: 16px; padding: 12px; border-radius: 8px;
      background: #00d4e8; color: #010408; font-weight: 600; text-decoration: none; }}
    .status {{ font-size: 0.85rem; margin-top: 12px; color: #40e8a8; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Émo Desktop</h1>
    <p>Confirmez la liaison sur <strong>Emo Online</strong> avec le compte connecté sur le site.</p>
    <div class="code">{code}</div>
    <a class="btn" href="{link}">Continuer sur Emo Online →</a>
    <p class="status">{status}</p>
    <p style="font-size:0.75rem;margin-top:16px">Si vous n&apos;êtes pas connecté, le site vous demandera vos identifiants puis affichera la page de confirmation.</p>
  </div>
</body>
</html>"""


def broadcast_log(message: str) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "message": message}
    dead = []
    for ws in _log_subscribers:
        try:
            asyncio.create_task(ws.send_json(entry))
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _log_subscribers:
            _log_subscribers.remove(ws)


def _get_pair_code() -> str:
    global _pair_code
    if _pair_code:
        return _pair_code
    cfg = load_config()
    code = (cfg.get("dashboard_pair_code") or "").strip()
    if not code:
        code = secrets.token_hex(3).upper()
        cfg["dashboard_pair_code"] = code
        save_config(cfg)
    _pair_code = code
    return code


def create_app() -> Any:
    if FastAPI is None:
        raise ImportError("fastapi et uvicorn requis: pip install fastapi uvicorn websockets")

    app = FastAPI(title="Emo Desktop Dashboard", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"service": "emo-desktop", "pair_required": True}

    @app.get("/pair")
    async def pair_info(request: Request):
        cfg = load_config()
        port = int(cfg.get("dashboard_port") or 8000)
        code = _get_pair_code()
        payload = {
            "code": code,
            "port": port,
            "site_url": cfg.get("site_url") or "https://xeroxytb.com",
            "site_link": site_link_url(code, port),
            "hint": "Connectez le desktop à Emo Online",
            "cloud_site": "https://xeroxytb.com/chat",
            "logged_in": bool((cfg.get("session_token") or "").strip()),
            "email": cfg.get("user_email", ""),
        }
        accept = (request.headers.get("accept") or "").lower()
        if "text/html" in accept and "application/json" not in accept.split(",")[0].strip():
            return HTMLResponse(_pair_html(payload))
        return payload

    @app.post("/pair")
    async def pair_verify(body: dict):
        code = (body.get("code") or "").strip().upper()
        email = (body.get("email") or "").strip()
        password = body.get("password") or ""
        session_token = (body.get("session_token") or "").strip()
        agent_token = (body.get("agent_token") or "").strip()

        # Appairage depuis le site (code + tokens cloud)
        if code and session_token:
            if code != _get_pair_code():
                return {"ok": False, "error": "Code d'appairage invalide"}
            conv = await _save_cloud_tokens(session_token, agent_token)
            paired_email = (body.get("email") or "").strip()
            if paired_email:
                cfg = load_config()
                cfg["user_email"] = paired_email
                save_config(cfg)
            _notify_paired("site")
            return {
                "ok": True,
                "type": "site_paired",
                "email": load_config().get("user_email", ""),
                "conversation_id": conv.get("conversation_id"),
            }

        # Connexion directe email / mot de passe (page /pair locale)
        if email and password:
            from emo.desktop.cloud_client import CloudClient

            client = CloudClient()
            result = await client.login(email, password)
            if result.get("ok"):
                _notify_paired("dashboard")
                return {"ok": True, "email": result.get("email"), "type": "cloud_login"}
            return {"ok": False, "error": result.get("error", "Échec login")}

        # Tokens collés manuellement (sans code)
        if session_token:
            conv = await _save_cloud_tokens(session_token, agent_token)
            _notify_paired("tokens")
            return {"ok": True, "type": "tokens_saved", "conversation_id": conv.get("conversation_id")}

        # Vérification code seul (mobile)
        if code and code == _get_pair_code():
            return {"ok": True, "type": "code_valid", "message": "Code valide — envoyez session_token depuis le site."}

        return {"ok": False, "error": "Code invalide ou identifiants manquants"}

    @app.post("/command")
    async def command(body: dict):
        text = (body.get("text") or body.get("command") or "").strip()
        if not text:
            return {"ok": False, "error": "commande vide"}
        broadcast_log(f"[mobile] {text}")
        if _wake_handler:
            try:
                _wake_handler()
            except Exception:
                pass
        if _command_handler:
            try:
                result = _command_handler(text)
                if hasattr(result, "__await__"):
                    result = await result
                return {"ok": True, "result": str(result)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True, "queued": text}

    @app.post("/api/wake")
    async def wake_ep():
        if _wake_handler:
            try:
                _wake_handler()
            except Exception:
                pass
        return {"ok": True}

    @app.websocket("/ws/phone-audio")
    async def phone_audio_ws(websocket: WebSocket):
        await websocket.accept()
        broadcast_log("SYS: Microphone téléphone actif.")
        q = get_phone_audio_queue()
        try:
            while True:
                data = await websocket.receive_bytes()
                try:
                    q.put_nowait({"data": data, "mime_type": "audio/pcm"})
                except asyncio.QueueFull:
                    pass
        except WebSocketDisconnect:
            pass
        finally:
            broadcast_log("SYS: Microphone téléphone arrêté.")
            if _live_session_ref is not None:
                _live_session_ref._phone_active = False

    @app.post("/upload")
    async def upload(file: UploadFile = File(...)):
        upload_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest = upload_dir / file.filename
        content = await file.read()
        dest.write_bytes(content)
        broadcast_log(f"Upload: {dest.name} ({len(content)} octets)")
        return {"ok": True, "path": str(dest), "bytes": len(content)}

    @app.websocket("/ws/log")
    async def ws_log(websocket: WebSocket):
        await websocket.accept()
        _log_subscribers.append(websocket)
        try:
            await websocket.send_json({"ts": datetime.now(timezone.utc).isoformat(), "message": "Connecté au journal Emo"})
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            if websocket in _log_subscribers:
                _log_subscribers.remove(websocket)

    return app


class DashboardServer(threading.Thread):
    def __init__(
        self,
        port: int = 8000,
        command_handler=None,
        pair_handler=None,
        wake_handler=None,
        phone_audio_handler=None,
    ):
        super().__init__(daemon=True, name="emo-dashboard")
        self.port = port
        self.command_handler = command_handler
        self.pair_handler = pair_handler
        self.wake_handler = wake_handler
        self.phone_audio_handler = phone_audio_handler
        self._server = None

    def run(self) -> None:
        if uvicorn is None:
            return
        if self.command_handler:
            set_command_handler(self.command_handler)
        if self.pair_handler:
            set_pair_handler(self.pair_handler)
        if self.wake_handler:
            set_wake_handler(self.wake_handler)
        if self.phone_audio_handler:
            set_phone_audio_handler(self.phone_audio_handler)
        app = create_app()
        config = uvicorn.Config(app, host="0.0.0.0", port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        asyncio.run(self._server.serve())

    def stop(self, timeout: float = 3.0) -> None:
        if self._server:
            self._server.should_exit = True
        if self.is_alive():
            self.join(timeout=timeout)
