"""Exécution des outils Gemini Live — port Mark-XLVIII."""
from __future__ import annotations

import asyncio
import os
import threading
import time
import traceback
from typing import Any, Callable

from google.genai import types

from emo.desktop.actions.skill_loader import run_skill
from emo.desktop.core.memory_manager import update_memory

# Outil Gemini → skill emo.desktop.actions
_TOOL_TO_SKILL: dict[str, str] = {
    "open_app": "open_app",
    "web_search": "web_search",
    "weather_report": "weather_report",
    "send_message": "send_message",
    "reminder": "reminder",
    "youtube_video": "youtube_video",
    "screen_processor": "screen_processor",
    "computer_settings": "computer_settings",
    "browser_control": "browser_control",
    "file_controller": "file_controller",
    "desktop_control": "desktop_control",
    "code_helper": "code_helper",
    "dev_agent_skill": "dev_agent_skill",
    "fallback_agent": "fallback_agent",
    "computer_control": "computer_control",
    "game_updater": "game_updater",
    "flight_finder": "flight_finder",
    "system_monitor_skill": "system_monitor_skill",
    "file_processor": "file_processor",
}


def _result_text(raw: Any) -> str:
    if raw is None:
        return "Done."
    if isinstance(raw, dict):
        if raw.get("message"):
            return str(raw["message"])
        if raw.get("error"):
            return str(raw["error"])
        if raw.get("ok") is False:
            return str(raw.get("error") or raw)
    return str(raw)


def _normalize_args(name: str, args: dict, *, agent_folder: str, current_file: str) -> dict:
    params = dict(args or {})

    if name == "open_app":
        app = params.get("app_name") or params.get("query") or ""
        return {"query": app}

    if name == "screen_processor":
        text = params.get("text") or params.get("prompt") or params.get("user_text") or ""
        return {
            "angle": (params.get("angle") or "screen").lower(),
            "text": text,
            "prompt": text,
        }

    if name == "run_custom_skill":
        skill_name = params.pop("skill_name", "")
        query = params.pop("query", "")
        out = {"query": query, **params}
        if query and "task" not in out:
            out["task"] = query
        return {"_skill_name": skill_name, **out}

    if name == "file_processor":
        if not params.get("file_path") and current_file:
            params["file_path"] = current_file
        if params.get("file_path") and not params.get("path"):
            params["path"] = params["file_path"]
        return params

    if name == "fallback_agent" and not params.get("folder") and agent_folder:
        params["folder"] = agent_folder

    return params


async def execute_tool(
    fc,
    *,
    on_log: Callable[[str], None] | None = None,
    on_state: Callable[[str], None] | None = None,
    speak: Callable[[str], None] | None = None,
    agent_folder: str = "",
    current_file: str = "",
    vision_hooks: Any | None = None,
    on_shutdown: Callable[[], None] | None = None,
    on_close_camera: Callable[[], None] | None = None,
) -> types.FunctionResponse:
    name = fc.name
    args = dict(fc.args or {})

    def _log(msg: str) -> None:
        if on_log:
            try:
                on_log(msg)
            except Exception:
                pass

    if on_state:
        try:
            on_state("THINKING")
        except Exception:
            pass

    _log(f"TOOL: {name} {args}")

    if name == "save_memory":
        category = args.get("category", "notes")
        key = args.get("key", "")
        value = args.get("value", "")
        if key and value:
            update_memory({category: {key: {"value": value}}})
            _log(f"Memory: {category}/{key} = {value}")
        if on_state:
            try:
                on_state("LISTENING")
            except Exception:
                pass
        return types.FunctionResponse(
            id=fc.id,
            name=name,
            response={"result": "ok", "silent": True},
        )

    loop = asyncio.get_event_loop()
    result = "Done."

    try:
        if name == "shutdown_jarvis":
            _log("SYS: Shutdown requested.")
            if speak:
                speak("Goodbye.")
            if on_shutdown:
                on_shutdown()
            else:
                def _exit():
                    time.sleep(1)
                    os._exit(0)

                threading.Thread(target=_exit, daemon=True).start()
            result = "Shutting down."

        elif name == "close_camera":
            if on_close_camera:
                on_close_camera()
            result = "Camera closed."

        elif name == "screen_processor":
            hooks = vision_hooks
            now = time.monotonic()
            cooldown = 4.0
            if hooks and (
                hooks.get("busy")
                or (now - hooks.get("last_time", 0.0)) < cooldown
            ):
                wait = max(0, cooldown - (now - hooks.get("last_time", 0.0)))
                _log(f"Vision cooldown ({wait:.1f}s)")
                result = (
                    "Vision is still processing the previous request. "
                    "I will not call this again."
                )
            else:
                from emo.desktop.actions import screen_processor as sp

                angle = (args.get("angle") or "screen").lower()
                user_text = args.get("text") or args.get("prompt") or "What do you see?"
                if angle == "camera":
                    img_b, mime_t = await loop.run_in_executor(None, sp.capture_camera)
                    stall = "camera"
                    if hooks is not None:
                        hooks["cam_active"] = True
                else:
                    img_b, mime_t = await loop.run_in_executor(None, sp.capture_screen)
                    stall = "screen"
                if hooks is not None:
                    hooks["busy"] = True
                    hooks["last_time"] = now
                    hooks["pending"] = (img_b, mime_t, user_text, angle)
                result = (
                    f"[VISION_ACTIVE] {stall.capitalize()} captured. "
                    f"Immediately say ONE natural sentence in the user's language. "
                    f"Do NOT describe or guess content — the actual image arrives in the NEXT message."
                )

        elif name == "run_custom_skill":
            skill_name = args.get("skill_name", "")
            norm = _normalize_args(name, args, agent_folder=agent_folder, current_file=current_file)
            skill_name = norm.pop("_skill_name", skill_name)
            raw = await loop.run_in_executor(None, lambda: run_skill(skill_name, norm))
            result = _result_text(raw)

        elif name in _TOOL_TO_SKILL:
            skill = _TOOL_TO_SKILL[name]
            norm = _normalize_args(name, args, agent_folder=agent_folder, current_file=current_file)
            raw = await loop.run_in_executor(None, lambda: run_skill(skill, norm))
            result = _result_text(raw)

        else:
            result = f"Unknown tool: {name}"

    except Exception as e:
        result = f"Tool '{name}' failed: {e}"
        traceback.print_exc()
        if speak:
            speak(f"Tool {name} failed.")

    if on_state:
        try:
            on_state("LISTENING")
        except Exception:
            pass

    _log(f"TOOL result {name}: {str(result)[:80]}")
    return types.FunctionResponse(
        id=fc.id,
        name=name,
        response={"result": result},
    )
