"""Multi-provider LlmChat — OpenAI, Claude, DeepSeek, Gemini, Groq, OpenRouter."""
from __future__ import annotations

import ssl_fix  # noqa: F401

import json
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import httpx

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None  # type: ignore

from llm_config import get_api_key


@dataclass
class UserMessage:
    text: str
    images: list[str] = field(default_factory=list)
    image_media_type: str = "image/jpeg"
    image_media_types: list[str] = field(default_factory=list)


def _media_types_for(images: list[str], media_type: str, media_types: list[str]) -> list[str]:
    if not images:
        return []
    if media_types and len(media_types) >= len(images):
        return media_types[: len(images)]
    if media_types:
        fallback = media_types[0]
        return [media_types[i] if i < len(media_types) else fallback for i in range(len(images))]
    return [media_type] * len(images)


@dataclass
class TextDelta:
    content: str


@dataclass
class ToolCallStart:
    id: str
    name: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolCallReady:
    tool_call: ToolCall


@dataclass
class StreamDone:
    tool_calls: list[ToolCall] = field(default_factory=list)


def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
    out: list[dict] = []
    for tool in tools or []:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if not fn:
            continue
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    out: list[dict] = []
    for tool in tools or []:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if fn:
            out.append({"type": "function", "function": fn})
    return out


def _normalize_messages(initial_messages: list[dict], system_message: str) -> tuple[str, list[dict]]:
    system = (system_message or "").strip()
    messages: list[dict] = []
    for msg in initial_messages or []:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            if content and content not in system:
                system = f"{system}\n\n{content}".strip()
            continue
        if role in ("user", "assistant"):
            entry: dict[str, Any] = {"role": role, "content": content}
            if role == "user" and msg.get("images"):
                entry["images"] = msg["images"]
                if msg.get("image_media_types"):
                    entry["image_media_types"] = msg["image_media_types"]
                elif msg.get("image_media_type"):
                    entry["image_media_type"] = msg["image_media_type"]
            messages.append(entry)
    return system, messages


def _build_user_content(
    text: str,
    images: list[str],
    media_type: str = "image/jpeg",
    media_types: list[str] | None = None,
) -> Any:
    if not images:
        return text
    mimes = _media_types_for(images, media_type, media_types or [])
    blocks: list[dict] = []
    for idx, img in enumerate(images[:4]):
        b64 = img.split(",", 1)[-1] if img.startswith("data:") else img
        mime = mimes[idx] if idx < len(mimes) else media_type
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64},
        })
    blocks.append({"type": "text", "text": text or "Analyse cette image."})
    return blocks


def _openai_user_content(
    text: str,
    images: list[str],
    media_type: str = "image/jpeg",
    media_types: list[str] | None = None,
) -> Any:
    if not images:
        return text
    mimes = _media_types_for(images, media_type, media_types or [])
    parts: list[dict] = [{"type": "text", "text": text or "Analyse cette image."}]
    for idx, img in enumerate(images[:4]):
        b64 = img.split(",", 1)[-1] if img.startswith("data:") else img
        mime = mimes[idx] if idx < len(mimes) else media_type
        if img.startswith("data:"):
            mime = img.split(";")[0].split(":")[1] if ";" in img else mime
        parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })
    return parts


def _gemini_user_parts(
    text: str,
    images: list[str],
    media_type: str = "image/jpeg",
    media_types: list[str] | None = None,
) -> list[dict]:
    mimes = _media_types_for(images, media_type, media_types or [])
    parts: list[dict] = [{"text": text or "Analyse cette image."}]
    for idx, img in enumerate(images[:4]):
        b64 = img.split(",", 1)[-1] if img.startswith("data:") else img
        mime = mimes[idx] if idx < len(mimes) else media_type
        if img.startswith("data:"):
            mime = img.split(";")[0].split(":")[1] if ";" in img else mime
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
    return parts


class LlmChat:
    def __init__(
        self,
        api_key: str = "",
        session_id: str = "",
        system_message: str = "",
        initial_messages: Optional[list[dict]] = None,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-20250514",
    ):
        self._fallback_key = api_key
        self._session_id = session_id
        self._system_message, self._messages = _normalize_messages(initial_messages or [], system_message)
        self._provider = provider
        self._model = model
        self._raw_tools: list[dict] = []
        self._anthropic_tools: list[dict] = []
        self._openai_tools: list[dict] = []

    def with_model(self, provider: str, model: str) -> "LlmChat":
        if provider and model:
            self._provider = provider
            self._model = model
        return self

    def with_tools(self, tools: list[dict]) -> "LlmChat":
        self._raw_tools = tools or []
        self._anthropic_tools = _to_anthropic_tools(tools)
        self._openai_tools = _to_openai_tools(tools)
        return self

    def add_tool_result(self, tool_use_id: str, result: str) -> None:
        if self._provider == "anthropic":
            self._messages.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": result}],
            })
        else:
            self._messages.append({
                "role": "tool",
                "tool_call_id": tool_use_id,
                "content": result,
            })

    async def send_message(self, user_message: UserMessage) -> str:
        parts: list[str] = []
        async for ev in self.stream_message(user_message):
            if isinstance(ev, TextDelta):
                parts.append(ev.content)
        return "".join(parts)

    async def stream_message(self, user_message: Optional[UserMessage] = None) -> AsyncIterator[Any]:
        if user_message is not None:
            imgs = user_message.images or []
            if imgs:
                entry: dict[str, Any] = {
                    "role": "user",
                    "content": user_message.text,
                    "images": imgs,
                    "image_media_type": user_message.image_media_type,
                }
                if user_message.image_media_types:
                    entry["image_media_types"] = user_message.image_media_types
                self._messages.append(entry)
            else:
                self._messages.append({"role": "user", "content": user_message.text})

        if self._provider == "anthropic":
            async for ev in self._stream_anthropic():
                yield ev
        elif self._provider == "gemini":
            async for ev in self._stream_gemini():
                yield ev
        elif self._provider == "huggingface":
            async for ev in self._stream_openai_compat():
                yield ev
        elif self._provider in ("groq", "openrouter", "openai", "deepseek"):
            async for ev in self._stream_openai_compat():
                yield ev
        else:
            async for ev in self._stream_openai_compat():
                yield ev

    def _key(self) -> str:
        key = get_api_key(self._provider, self._fallback_key)
        if not key:
            raise ValueError(f"Clé API manquante pour {self._provider}")
        return key

    async def _ensure_stream_ok(self, resp: httpx.Response) -> None:
        if resp.is_error:
            await resp.aread()
        resp.raise_for_status()

    def _anthropic_messages(self) -> list[dict]:
        out: list[dict] = []
        for m in self._messages:
            role = m.get("role")
            content = m.get("content")
            if role == "user" and m.get("images"):
                out.append({
                    "role": "user",
                    "content": _build_user_content(
                        str(content or ""),
                        m.get("images") or [],
                        m.get("image_media_type") or "image/jpeg",
                        m.get("image_media_types"),
                    ),
                })
            elif role in ("user", "assistant"):
                out.append({"role": role, "content": content if content is not None else ""})
        return out

    async def _stream_anthropic(self) -> AsyncIterator[Any]:
        if AsyncAnthropic is None:
            raise ValueError("Package anthropic non installé")
        client = AsyncAnthropic(api_key=self._key())
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 8192,
            "system": self._system_message,
            "messages": self._anthropic_messages(),
        }
        if self._anthropic_tools:
            kwargs["tools"] = self._anthropic_tools

        tool_calls: list[ToolCall] = []
        assistant_blocks: list[dict] = []
        current_tool: dict[str, Any] | None = None
        turn_text = ""

        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                etype = getattr(event, "type", None)
                if etype == "content_block_start":
                    block = event.content_block
                    if getattr(block, "type", None) == "tool_use":
                        current_tool = {"id": block.id, "name": block.name, "input_json": ""}
                        yield ToolCallStart(id=block.id, name=block.name)
                elif etype == "content_block_delta":
                    delta = event.delta
                    dtype = getattr(delta, "type", None)
                    if dtype == "text_delta":
                        turn_text += delta.text
                        yield TextDelta(content=delta.text)
                    elif dtype == "input_json_delta" and current_tool is not None:
                        current_tool["input_json"] += delta.partial_json
                elif etype == "content_block_stop" and current_tool is not None:
                    try:
                        args = json.loads(current_tool["input_json"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    tc = ToolCall(id=current_tool["id"], name=current_tool["name"], arguments=args)
                    tool_calls.append(tc)
                    assistant_blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                    yield ToolCallReady(tool_call=tc)
                    current_tool = None

            final = await stream.get_final_message()
            if turn_text:
                assistant_blocks.append({"type": "text", "text": turn_text})
            elif not assistant_blocks:
                for block in final.content:
                    if getattr(block, "type", None) == "text":
                        assistant_blocks.append({"type": "text", "text": block.text})

        if assistant_blocks:
            self._messages.append({"role": "assistant", "content": assistant_blocks})
        yield StreamDone(tool_calls=tool_calls)

    def _openai_base(self) -> tuple[str, dict]:
        auth = {"Authorization": f"Bearer {self._key()}"}
        if self._provider == "openai":
            return "https://api.openai.com/v1", auth
        if self._provider == "huggingface":
            return "https://router.huggingface.co/v1", auth
        if self._provider == "deepseek":
            return "https://api.deepseek.com", auth
        if self._provider == "groq":
            return "https://api.groq.com/openai/v1", auth
        return "https://openrouter.ai/api/v1", {
            **auth,
            "HTTP-Referer": os.environ.get("OPENROUTER_REFERER", "https://xeroxytb.com"),
            "X-Title": "Emo Online",
        }

    def _openai_messages(self) -> list[dict]:
        msgs = [{"role": "system", "content": self._system_message}] if self._system_message else []
        for m in self._messages:
            role = m.get("role")
            content = m.get("content")
            if role == "tool":
                tcid = m.get("tool_call_id") or ""
                if not tcid:
                    continue
                msgs.append({"role": "tool", "tool_call_id": tcid, "content": content or ""})
            elif role == "assistant":
                entry: dict[str, Any] = {"role": "assistant", "content": content if content is not None else ""}
                if m.get("tool_calls"):
                    entry["tool_calls"] = m["tool_calls"]
                msgs.append(entry)
            elif role == "user" and content is not None:
                imgs = m.get("images") or []
                if imgs:
                    msgs.append({
                        "role": "user",
                        "content": _openai_user_content(
                            str(content),
                            imgs,
                            m.get("image_media_type") or "image/jpeg",
                            m.get("image_media_types"),
                        ),
                    })
                else:
                    msgs.append({"role": "user", "content": content})
        return msgs

    async def _stream_openai_compat(self) -> AsyncIterator[Any]:
        base, headers = self._openai_base()
        headers["Content-Type"] = "application/json"
        max_tokens = 2048 if self._provider in ("groq", "huggingface") else 8192
        body: dict[str, Any] = {
            "model": self._model,
            "messages": self._openai_messages(),
            "max_tokens": max_tokens,
            "stream": True,
        }
        if self._openai_tools and self._provider != "huggingface":
            body["tools"] = self._openai_tools
            if self._provider == "groq":
                body["tool_choice"] = "auto"

        tool_calls: dict[int, dict] = {}
        turn_text = ""
        finish_reason = None

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{base}/chat/completions", headers=headers, json=body) as resp:
                if resp.is_error:
                    err_body = await resp.aread()
                    detail = err_body.decode("utf-8", errors="replace")[:500]
                    raise httpx.HTTPStatusError(
                        f"{self._provider} API {resp.status_code}: {detail}",
                        request=resp.request,
                        response=resp,
                    )
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    choice = (data.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    finish_reason = choice.get("finish_reason") or finish_reason
                    if delta.get("content"):
                        turn_text += delta["content"]
                        yield TextDelta(content=delta["content"])
                    for tc_delta in delta.get("tool_calls") or []:
                        idx = tc_delta.get("index", 0)
                        if idx not in tool_calls:
                            tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.get("id"):
                            tool_calls[idx]["id"] = tc_delta["id"]
                        fn = tc_delta.get("function") or {}
                        if fn.get("name"):
                            tool_calls[idx]["name"] = fn["name"]
                            yield ToolCallStart(id=tool_calls[idx]["id"] or f"call_{idx}", name=fn["name"])
                        if fn.get("arguments"):
                            tool_calls[idx]["arguments"] += fn["arguments"]

        parsed_tools: list[ToolCall] = []
        for idx in sorted(tool_calls.keys()):
            tc = tool_calls[idx]
            try:
                args = json.loads(tc["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            tcall = ToolCall(id=tc["id"] or f"call_{idx}", name=tc["name"], arguments=args)
            parsed_tools.append(tcall)
            yield ToolCallReady(tool_call=tcall)

        assistant_msg: dict[str, Any] = {"role": "assistant", "content": turn_text or ""}
        if parsed_tools:
            assistant_msg["tool_calls"] = [
                {"id": t.id, "type": "function", "function": {"name": t.name, "arguments": json.dumps(t.arguments)}}
                for t in parsed_tools
            ]
        self._messages.append(assistant_msg)
        yield StreamDone(tool_calls=parsed_tools if finish_reason == "tool_calls" or parsed_tools else [])

    async def _stream_gemini(self) -> AsyncIterator[Any]:
        key = self._key()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:streamGenerateContent?alt=sse&key={key}"
        contents = []
        for m in self._messages:
            role = m.get("role")
            content = m.get("content")
            if role == "tool":
                text = f"[Résultat outil {m.get('tool_call_id', '')}]: {content}"
                contents.append({"role": "user", "parts": [{"text": str(text)[:8000]}]})
            elif role == "user":
                imgs = m.get("images") or []
                if imgs:
                    parts = _gemini_user_parts(
                        str(content) if content is not None else "",
                        imgs,
                        m.get("image_media_type") or "image/jpeg",
                        m.get("image_media_types"),
                    )
                    contents.append({"role": "user", "parts": parts})
                else:
                    text = content if isinstance(content, str) else str(content)
                    contents.append({"role": "user", "parts": [{"text": text}]})
            elif role == "assistant":
                text = content if isinstance(content, str) else str(content)
                if m.get("tool_calls"):
                    text = (text or "") + "\n[Appels d'outils effectués]"
                contents.append({"role": "model", "parts": [{"text": text or "…"}]})

        payload = {
            "systemInstruction": {"parts": [{"text": self._system_message}]} if self._system_message else None,
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 8192},
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        turn_text = ""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                await self._ensure_stream_ok(resp)
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    for candidate in data.get("candidates") or []:
                        for part in (candidate.get("content") or {}).get("parts") or []:
                            if part.get("text"):
                                turn_text += part["text"]
                                yield TextDelta(content=part["text"])

        self._messages.append({"role": "assistant", "content": turn_text})
        yield StreamDone(tool_calls=[])
