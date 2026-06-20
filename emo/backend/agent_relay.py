"""Local agent relay via HTTP long-polling.

Per-user in-memory queue. The local agent long-polls /api/agent/poll for tool
requests, executes them on the user's PC, and POSTs results back. Heartbeats
mark the agent as online (TTL ~12s).
"""
import asyncio
import time
import uuid
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("emo.agent")

HEARTBEAT_TTL = 30.0  # seconds


class AgentRegistry:
    def __init__(self):
        # user_id -> last heartbeat timestamp
        self._heartbeats: Dict[str, float] = {}
        # user_id -> machine context from agent heartbeat (home, desktop, username, …)
        self._context: Dict[str, dict] = {}
        # user_id -> asyncio.Queue of {request_id, tool, args}
        self._queues: Dict[str, asyncio.Queue] = {}
        # request_id -> asyncio.Future
        self._pending: Dict[str, asyncio.Future] = {}

    def heartbeat(self, user_id: str, context: Optional[dict] = None):
        self._heartbeats[user_id] = time.time()
        if context:
            cleaned = {k: v for k, v in context.items() if v is not None and v != ""}
            if cleaned:
                self._context[user_id] = {**self._context.get(user_id, {}), **cleaned}

    def get_context(self, user_id: str) -> dict:
        return dict(self._context.get(user_id) or {})

    def set_context(self, user_id: str, context: dict):
        if context:
            self._context[user_id] = {**self._context.get(user_id, {}), **context}

    def is_online(self, user_id: str) -> bool:
        ts = self._heartbeats.get(user_id)
        return ts is not None and (time.time() - ts) < HEARTBEAT_TTL

    def _queue(self, user_id: str) -> asyncio.Queue:
        q = self._queues.get(user_id)
        if q is None:
            q = asyncio.Queue()
            self._queues[user_id] = q
        return q

    async def poll(self, user_id: str, timeout: float = 25.0) -> Optional[dict]:
        """Long-poll for a tool request. Returns None on timeout."""
        self.heartbeat(user_id)
        q = self._queue(user_id)
        try:
            req = await asyncio.wait_for(q.get(), timeout=timeout)
            return req
        except asyncio.TimeoutError:
            return None

    def resolve(self, request_id: str, payload: dict):
        fut = self._pending.get(request_id)
        if fut and not fut.done():
            # Defense-in-depth: cap stdout/stderr/content even if the agent forgot to.
            # Recursive `dir /s` on a whole drive can return MBs which would saturate
            # the SSE pipe and freeze the chat.
            fut.set_result(_truncate_large_fields(payload))

    async def dispatch(self, user_id: str, tool: str, args: dict, timeout: int = 90) -> dict:
        """Enqueue a tool request and wait for the agent's response."""
        if not self.is_online(user_id):
            return {"ok": False, "error": "Agent local non connecté. Télécharge et lance Emo-Agent depuis Profil > Agent ou le panneau Agent."}

        request_id = uuid.uuid4().hex
        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[request_id] = fut
        await self._queue(user_id).put({
            "id": request_id, "tool": tool, "args": args,
        })
        try:
            payload = await asyncio.wait_for(fut, timeout=timeout)
            if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
                return payload["result"]
            return payload
        except asyncio.TimeoutError:
            return {"ok": False, "error": f"Agent timeout après {timeout}s"}
        finally:
            self._pending.pop(request_id, None)


registry = AgentRegistry()


# 64 KB tail per field — keeps end of output (where errors usually live)
_MAX_FIELD_BYTES = 64 * 1024


def _truncate_large_fields(payload: dict) -> dict:
    """Trim very large stdout/stderr/content in tool results before they hit the chat stream."""
    if not isinstance(payload, dict):
        return payload
    result = payload.get("result")
    if not isinstance(result, dict):
        return payload
    changed = False
    for key in ("stdout", "stderr", "content"):
        val = result.get(key)
        if isinstance(val, str) and len(val) > _MAX_FIELD_BYTES:
            kept = val[-_MAX_FIELD_BYTES:]
            result[key] = (
                f"…[backend-truncated — kept last {_MAX_FIELD_BYTES // 1024} KB "
                f"of {len(val)} total bytes]…\n{kept}"
            )
            result[f"{key}_truncated"] = True
            changed = True
    if changed:
        logger.info("Truncated large agent result fields for request %s", payload.get("id"))
    return payload
