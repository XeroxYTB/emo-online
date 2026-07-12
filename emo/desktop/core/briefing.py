"""Briefing de démarrage — port Mark-XLVIII."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from google.genai import types

from emo.desktop.core.memory_manager import load_memory

if TYPE_CHECKING:
    from emo.desktop.core.live_session import EmoLiveSession


async def send_startup_briefing(session: "EmoLiveSession") -> None:
    """
    Two-phase briefing:
      Phase 1 — immediate greeting
      Phase 2 — news fetched in background
    """
    import asyncio

    await asyncio.sleep(0.3)
    if not session.session:
        return

    memory = load_memory() or {}
    identity = memory.get("identity", {})

    def _val(k: str) -> str:
        e = identity.get(k, {})
        return (e.get("value", "") if isinstance(e, dict) else str(e)).strip()

    lang = _val("language")
    name = _val("name")
    time_str = datetime.now().strftime("%H:%M")

    lang_clause = f" Respond in {lang}." if lang else ""
    name_clause = f" Address the user as {name}." if name else ""
    p1 = (
        f"Greet the user, mention it is {time_str}, and say you are fetching today's news headlines now. "
        f"One short sentence only. Do not call any tools.{lang_clause}{name_clause}"
    )

    await session.session.send_client_content(
        turns=cast(types.ContentDict, {"parts": [{"text": p1}]}),
        turn_complete=True,
    )
    session._log("SYS: Briefing phase 1 (greeting) sent.")

    async def _guarded_news():
        try:
            await briefing_news_phase(session, lang)
        except Exception as e:
            session._log(f"SYS: Briefing news phase failed: {e}")

    asyncio.create_task(_guarded_news())


async def briefing_news_phase(session: "EmoLiveSession", lang: str) -> None:
    import asyncio

    lang_str = f" Respond in {lang}." if lang else ""
    await asyncio.sleep(1.5)

    if not session.session:
        return

    p2 = (
        "[BRIEFING] Call web_search with mode='news' and query='top world news today' "
        "to find actual recent news articles with real event headlines (not just website names). "
        "After the search, say ONE specific news event from the results in one sentence, "
        f"then say the full list is displayed on screen.{lang_str}"
    )

    await session.session.send_client_content(
        turns=cast(types.ContentDict, {"parts": [{"text": p2}]}),
        turn_complete=True,
    )
    session._log("SYS: Briefing phase 2 (news) sent.")
