"""Pipeline think → plan → execute."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from emo.desktop.task_router import RouteResult, route_message


@dataclass
class BrainStep:
    phase: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)


class AgentBrain:
    """Cerveau agent: réflexion, planification, exécution."""

    def __init__(
        self,
        on_step: Callable[[BrainStep], None] | None = None,
        run_skill: Callable[[str, dict], Any] | None = None,
        run_dev: Callable[[str], Any] | None = None,
        chat: Callable[[str], Any] | None = None,
    ):
        self.on_step = on_step
        self.run_skill = run_skill
        self.run_dev = run_dev
        self.chat = chat
        self._interrupt = False

    def interrupt(self) -> None:
        self._interrupt = True

    def reset_interrupt(self) -> None:
        self._interrupt = False

    def _emit(self, phase: str, content: str, **data: Any) -> None:
        if self.on_step:
            self.on_step(BrainStep(phase=phase, content=content, data=data))

    async def process(self, message: str, *, agent_online: bool = False) -> str:
        self.reset_interrupt()
        route = route_message(message, agent_online=agent_online)
        self._emit("think", f"Route: {route.action} — {route.reason}", route=route.action)

        if self._interrupt:
            return "Interrompu."

        plan_lines = [f"1. Analyser: {message[:80]}", f"2. Action: {route.action}"]
        if route.skill:
            plan_lines.append(f"3. Skill: {route.skill}")
        self._emit("plan", "\n".join(plan_lines))

        if self._interrupt:
            return "Interrompu."

        result = await self._execute(route, message)
        self._emit("execute", "Terminé", result=result[:200] if result else "")
        return result

    async def _execute(self, route: RouteResult, message: str) -> str:
        if route.action == "run_skill" and route.skill and self.run_skill:
            out = self.run_skill(route.skill, route.args or {"query": message})
            if hasattr(out, "__await__"):
                out = await out
            return str(out)

        if route.action in ("dev", "run_project") and self.run_dev:
            out = self.run_dev(message)
            if hasattr(out, "__await__"):
                out = await out
            return str(out)

        if route.action == "code" and self.run_skill:
            out = self.run_skill("code_helper", {"prompt": message})
            if hasattr(out, "__await__"):
                out = await out
            return str(out)

        if route.action == "local":
            return "Commande locale — utilisez le relais agent cloud pour exec_shell/read_file."

        if self.chat:
            out = self.chat(message)
            if hasattr(out, "__await__"):
                out = await out
            return str(out)

        return f"Action {route.action} — pas de handler configuré."
