"""Session Gemini texte/voix avec repli httpx vers le backend cloud."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable

from emo.desktop.cloud_client import CloudClient
from emo.desktop.config import load_config


def _is_quota_error(exc: BaseException) -> bool:
    err = str(exc).lower()
    return any(
        k in err
        for k in ("429", "resource_exhausted", "quota exceeded", "quota", "rate limit")
    )


def _has_cloud_session() -> bool:
    return bool((load_config().get("session_token") or "").strip())


class GeminiSession:
    """Wrapper session IA — Gemini si clé dispo, sinon backend Emo."""

    def __init__(self, on_log: Callable[[str], None] | None = None):
        self.on_log = on_log
        self._genai = None
        self._quota_exhausted = False
        self._cloud = CloudClient(on_log=on_log)
        self._init_gemini()

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    def _init_gemini(self) -> None:
        cfg = load_config()
        key = (cfg.get("gemini_api_key") or "").strip()
        if not key:
            if not _has_cloud_session():
                self._log("Gemini: configurez gemini_api_key dans Paramètres (ou connectez le cloud).")
            return
        try:
            from google import genai  # type: ignore
            self._genai = genai.Client(api_key=key)
            self._log("Gemini: client initialisé")
        except ImportError:
            self._log("Gemini: installez google-genai pour la voix live")
        except Exception as e:
            self._log(f"Gemini: erreur init — {e}")

    @property
    def gemini_available(self) -> bool:
        return self._genai is not None and not self._quota_exhausted

    @property
    def quota_exhausted(self) -> bool:
        return self._quota_exhausted

    async def chat_text(self, message: str, history: list[dict] | None = None) -> str:
        """Réponse texte — cloud Emo Online si appairé, sinon Gemini avec repli cloud."""
        if _has_cloud_session():
            return await self._cloud_chat(message)

        if self._genai and not self._quota_exhausted:
            try:
                prompt = message
                if history:
                    ctx = "\n".join(
                        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-6:]
                    )
                    prompt = f"{ctx}\nuser: {message}"
                resp = self._genai.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                text = getattr(resp, "text", None) or str(resp)
                return text.strip()
            except Exception as e:
                if _is_quota_error(e):
                    self._quota_exhausted = True
                    self._log("Gemini: quota épuisé (429) — repli cloud Emo Online.")
                else:
                    self._log(f"Gemini erreur: {e} — repli cloud")

        return await self._cloud_chat(message)

    async def _cloud_chat(self, message: str) -> str:
        cfg = load_config()
        if not (cfg.get("session_token") or "").strip():
            return (
                "Mode cloud indisponible : connectez-vous à Emo Online "
                "(Paramètres → email/mot de passe) ou configurez gemini_api_key."
            )
        return await self._cloud.chat(message)

    def start_voice_session(self) -> dict[str, Any]:
        """Démarre session vocale Gemini Live ou retourne message de repli."""
        has_cloud = _has_cloud_session()
        if has_cloud or self._quota_exhausted:
            return {
                "ok": True,
                "message": (
                    "Mode vocal : micro Gemini Live (STT) + réponses cloud "
                    "+ voix Charon via Live (repli edge-tts si indisponible)."
                ),
                "mode": "cloud_hybrid",
            }
        if not self._genai:
            return {
                "ok": False,
                "message": "Configurez gemini_api_key ou connectez-vous à Emo Online.",
            }
        return {
            "ok": True,
            "message": "Mode vocal : Gemini Live Mark-XLVIII (micro + voix Charon).",
            "mode": "gemini_live",
        }

    async def stream_voice_placeholder(self) -> AsyncIterator[str]:
        """Générateur stub pour flux vocal."""
        yield "Mode vocal actif — parlez au micro."
