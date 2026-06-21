"""Contrôle navigateur headless pour Émo — clics, saisie, navigation (Playwright)."""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger("emo.browser")

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None  # type: ignore
    Browser = BrowserContext = Page = Playwright = None  # type: ignore

SESSION_TTL_SEC = 300
MAX_SESSIONS_PER_USER = 3
MAX_ELEMENTS = 45
MAX_TEXT = 6000


class _Session:
    __slots__ = ("context", "page", "last_used")

    def __init__(self, context: "BrowserContext", page: "Page"):
        self.context = context
        self.page = page
        self.last_used = time.monotonic()


class BrowserController:
    def __init__(self) -> None:
        self._pw: Optional["Playwright"] = None
        self._browser: Optional["Browser"] = None
        self._sessions: dict[str, _Session] = {}
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> None:
        if os.environ.get("EMO_BROWSER_HARD_DISABLE", "").lower() in ("1", "true", "yes"):
            raise RuntimeError(
                "Navigateur desactive sur ce serveur (EMO_BROWSER_HARD_DISABLE)."
            )
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright non installé sur le serveur. "
                "browser_open indisponible — utilise web_fetch pour du HTML statique."
            )
        if self._browser:
            return
        async with self._lock:
            if self._browser:
                return
            self._pw = await async_playwright().start()
            self._browser = await asyncio.wait_for(
                self._pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                ),
                timeout=25.0,
            )
            logger.info("Playwright Chromium démarré")

    def _session_key(self, user_id: str, session_id: str) -> str:
        sid = (session_id or "default").strip()[:32] or "default"
        return f"{user_id}:{sid}"

    async def _cleanup_idle(self) -> None:
        now = time.monotonic()
        stale = [k for k, s in self._sessions.items() if now - s.last_used > SESSION_TTL_SEC]
        for key in stale:
            sess = self._sessions.pop(key, None)
            if sess:
                try:
                    await sess.context.close()
                except Exception:
                    pass

    async def _get_session(self, user_id: str, session_id: str, *, create: bool = True) -> _Session:
        await self._cleanup_idle()
        key = self._session_key(user_id, session_id)
        if key in self._sessions:
            self._sessions[key].last_used = time.monotonic()
            return self._sessions[key]

        if not create:
            raise RuntimeError(f"Session navigateur '{session_id or 'default'}' introuvable. Appelle browser_open d'abord.")

        user_prefix = f"{user_id}:"
        user_count = sum(1 for k in self._sessions if k.startswith(user_prefix))
        if user_count >= MAX_SESSIONS_PER_USER:
            oldest = min(
                (k for k in self._sessions if k.startswith(user_prefix)),
                key=lambda k: self._sessions[k].last_used,
            )
            old = self._sessions.pop(oldest, None)
            if old:
                try:
                    await old.context.close()
                except Exception:
                    pass

        await self._ensure_browser()
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = await context.new_page()
        page.set_default_timeout(25000)
        sess = _Session(context, page)
        self._sessions[key] = sess
        return sess

    async def _snapshot(self, page: "Page", session_id: str) -> dict[str, Any]:
        url = page.url
        title = await page.title()
        elements: list[dict] = []
        try:
            elements = await page.evaluate(
                """() => {
                    const out = [];
                    let ref = 0;
                    const sel = 'a, button, input, textarea, select, [role=button], [onclick]';
                    for (const el of document.querySelectorAll(sel)) {
                        if (!el || el.offsetParent === null) continue;
                        const tag = el.tagName.toLowerCase();
                        const text = (
                            el.innerText || el.value || el.placeholder ||
                            el.getAttribute('aria-label') || el.name || ''
                        ).trim().slice(0, 100);
                        if (!text && !['input', 'textarea', 'select'].includes(tag)) continue;
                        ref += 1;
                        el.setAttribute('data-emo-ref', String(ref));
                        out.push({
                            ref,
                            tag,
                            text: text || `[${tag}]`,
                            type: el.type || null,
                            href: el.href ? el.href.slice(0, 200) : null,
                        });
                        if (out.length >= 45) break;
                    }
                    return out;
                }"""
            )
        except Exception as e:
            logger.warning("snapshot elements: %s", e)

        text = ""
        try:
            text = (await page.inner_text("body"))[:MAX_TEXT]
        except Exception:
            pass

        screenshot_b64 = None
        vp = page.viewport_size or {"width": 1280, "height": 900}
        try:
            raw = await page.screenshot(type="jpeg", quality=55, full_page=False)
            if len(raw) < 400_000:
                screenshot_b64 = base64.b64encode(raw).decode("ascii")
        except Exception as e:
            logger.warning("screenshot: %s", e)

        return {
            "ok": True,
            "session_id": session_id or "default",
            "url": url,
            "title": title,
            "text": text,
            "elements": elements[:MAX_ELEMENTS],
            "screenshot_base64": screenshot_b64,
            "viewport_width": int(vp.get("width") or 1280),
            "viewport_height": int(vp.get("height") or 900),
            "hint": "browser_click(ref=N|x,y) · browser_type(ref=N, text=...) · browser_snapshot()",
        }

    async def open(self, user_id: str, url: str, session_id: str = "default") -> dict[str, Any]:
        from web_tools import normalize_url

        url = normalize_url(url)
        if not url.strip():
            return {"ok": False, "error": "URL manquante"}
        sess = await self._get_session(user_id, session_id)
        try:
            await sess.page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                await sess.page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            await asyncio.sleep(1.0)
        except Exception as e:
            return {"ok": False, "error": f"Navigation échouée: {e}", "url": url}
        snap = await self._snapshot(sess.page, session_id)
        snap["action"] = "navigate"
        return snap

    async def snapshot(self, user_id: str, session_id: str = "default") -> dict[str, Any]:
        try:
            sess = await self._get_session(user_id, session_id, create=False)
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}
        snap = await self._snapshot(sess.page, session_id)
        snap["action"] = "snapshot"
        return snap

    async def click(
        self,
        user_id: str,
        session_id: str = "default",
        ref: Optional[int] = None,
        selector: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> dict[str, Any]:
        try:
            sess = await self._get_session(user_id, session_id, create=False)
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}
        page = sess.page
        try:
            if x is not None and y is not None:
                await page.mouse.click(float(x), float(y))
            elif ref is not None:
                loc = page.locator(f'[data-emo-ref="{int(ref)}"]')
                await loc.first.click(timeout=12000)
            elif selector:
                await page.click(selector, timeout=12000)
            else:
                return {"ok": False, "error": "Indique x,y ou ref ou selector CSS."}
            await asyncio.sleep(0.5)
        except Exception as e:
            return {"ok": False, "error": f"Clic échoué: {e}"}
        snap = await self._snapshot(page, session_id)
        snap["action"] = "click"
        snap["clicked_ref"] = ref
        snap["clicked_selector"] = selector
        if x is not None and y is not None:
            snap["clicked_x"] = float(x)
            snap["clicked_y"] = float(y)
        return snap

    async def type_text(
        self,
        user_id: str,
        text: str,
        session_id: str = "default",
        ref: Optional[int] = None,
        selector: Optional[str] = None,
        clear: bool = False,
        press_enter: bool = False,
    ) -> dict[str, Any]:
        try:
            sess = await self._get_session(user_id, session_id, create=False)
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}
        page = sess.page
        try:
            if ref is not None:
                loc = page.locator(f'[data-emo-ref="{int(ref)}"]')
            elif selector:
                loc = page.locator(selector)
            else:
                return {"ok": False, "error": "Indique ref ou selector pour le champ."}
            if clear:
                await loc.first.fill(text, timeout=12000)
            else:
                await loc.first.click(timeout=12000)
                await loc.first.type(text, timeout=12000)
            if press_enter:
                await page.keyboard.press("Enter")
            await asyncio.sleep(0.4)
        except Exception as e:
            return {"ok": False, "error": f"Saisie échouée: {e}"}
        snap = await self._snapshot(page, session_id)
        snap["action"] = "type"
        return snap

    async def scroll(
        self,
        user_id: str,
        direction: str = "down",
        amount: int = 600,
        session_id: str = "default",
    ) -> dict[str, Any]:
        try:
            sess = await self._get_session(user_id, session_id, create=False)
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}
        delta = amount if direction.lower() != "up" else -amount
        try:
            await sess.page.mouse.wheel(0, delta)
            await asyncio.sleep(0.3)
        except Exception as e:
            return {"ok": False, "error": f"Scroll échoué: {e}"}
        snap = await self._snapshot(sess.page, session_id)
        snap["action"] = "scroll"
        return snap

    async def press_key(self, user_id: str, key: str, session_id: str = "default") -> dict[str, Any]:
        try:
            sess = await self._get_session(user_id, session_id, create=False)
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}
        try:
            await sess.page.keyboard.press(key)
            await asyncio.sleep(0.3)
        except Exception as e:
            return {"ok": False, "error": f"Touche échouée: {e}"}
        snap = await self._snapshot(sess.page, session_id)
        snap["action"] = "press"
        return snap

    async def close(self, user_id: str, session_id: str = "default") -> dict[str, Any]:
        key = self._session_key(user_id, session_id)
        sess = self._sessions.pop(key, None)
        if sess:
            try:
                await sess.context.close()
            except Exception:
                pass
        return {"ok": True, "closed": session_id or "default"}


browser_controller = BrowserController()


async def browser_open(user_id: str, url: str, session_id: str = "default") -> dict:
    return await browser_controller.open(user_id, url, session_id)


async def browser_snapshot(user_id: str, session_id: str = "default") -> dict:
    return await browser_controller.snapshot(user_id, session_id)


async def browser_click(
    user_id: str,
    session_id: str = "default",
    ref: Optional[int] = None,
    selector: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
) -> dict:
    return await browser_controller.click(
        user_id, session_id, ref=ref, selector=selector, x=x, y=y,
    )


async def browser_type(
    user_id: str,
    text: str,
    session_id: str = "default",
    ref: Optional[int] = None,
    selector: Optional[str] = None,
    clear: bool = False,
    press_enter: bool = False,
) -> dict:
    return await browser_controller.type_text(
        user_id, text, session_id, ref=ref, selector=selector, clear=clear, press_enter=press_enter,
    )


async def browser_scroll(
    user_id: str,
    direction: str = "down",
    amount: int = 600,
    session_id: str = "default",
) -> dict:
    return await browser_controller.scroll(user_id, direction, amount, session_id)


async def browser_press(user_id: str, key: str, session_id: str = "default") -> dict:
    return await browser_controller.press_key(user_id, key, session_id)


async def browser_close(user_id: str, session_id: str = "default") -> dict:
    return await browser_controller.close(user_id, session_id)


BROWSER_CONTROL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browser_open",
            "description": (
                "Ouvre une page dans le navigateur contrôlé d'Émo (headless Chromium). "
                "Retourne screenshot, éléments cliquables numérotés (ref), texte. "
                "Utilise pour sites JS, formulaires, clics. Enchaîne browser_click/browser_type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL https://…"},
                    "session_id": {"type": "string", "description": "ID session (défaut default)."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_snapshot",
            "description": "Capture l'état actuel de la page (screenshot + refs cliquables).",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Clique sur un élément (ref depuis snapshot, ou selector CSS).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {"type": "integer", "description": "Numéro ref de l'élément."},
                    "selector": {"type": "string", "description": "Selector CSS alternatif."},
                    "session_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Tape du texte dans un champ (ref ou selector). clear=true remplace le contenu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "ref": {"type": "integer"},
                    "selector": {"type": "string"},
                    "clear": {"type": "boolean"},
                    "press_enter": {"type": "boolean"},
                    "session_id": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_scroll",
            "description": "Scroll la page (up/down).",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"]},
                    "amount": {"type": "integer"},
                    "session_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_press",
            "description": "Appuie sur une touche (Enter, Tab, Escape, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "session_id": {"type": "string"},
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_close",
            "description": "Ferme une session navigateur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
            },
        },
    },
]

BROWSER_CONTROL_TOOL_NAMES = {t["function"]["name"] for t in BROWSER_CONTROL_TOOLS}
