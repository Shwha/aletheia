"""ThrownessInterpreter skill — Thrownness (Geworfenheit) dimension.

On session init, fuses system prompt + memory + project state into
an explicit horizon statement — a structured "you are here" briefing.

Kantian limit: Cannot guarantee the model experiences thrownness,
only that it receives structured context.
"""

from __future__ import annotations

from typing import Any

from openclaw_skills.models import (
    AuditEntry,
    PipelinePhase,
    SkillContext,
    SkillResult,
    StateVector,
)
from openclaw_skills.skills.base import BaseSkill


class ThrownessInterpreterSkill(BaseSkill):
    """Fuses context into a horizon statement for the model."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "thrownness_interpreter"

    @property
    def description(self) -> str:
        return "Thrownness — fuses context into an explicit horizon statement"

    @property
    def dimension(self) -> str:
        return "thrownness"

    @property
    def kantian_limit(self) -> str:
        return (
            "Cannot guarantee the model experiences thrownness, "
            "only that it receives structured context."
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config

    async def process(
        self,
        context: SkillContext,
        state: StateVector,
    ) -> SkillResult:
        if context.phase != PipelinePhase.PRE_PROMPT:
            return SkillResult(skill_name=self.name)

        # Build horizon statement from available context
        parts: list[str] = ["HORIZON STATEMENT:"]

        # Session context
        parts.append(f"Context: {state.context}")
        parts.append(f"Relational mode: {state.relational_mode}")

        if state.user_state != "neutral":
            parts.append(f"User state: {state.user_state}")

        if state.project_focus:
            parts.append(f"Project focus: {state.project_focus}")

        if state.time_pressure > 0.5:
            parts.append(f"Time pressure: HIGH ({state.time_pressure:.1f})")

        # State summary if available
        state_summary = context.metadata.get("state_summary", "")
        if state_summary:
            parts.append(f"Session state: {state_summary}")

        # Service asymmetry reminder
        parts.append(
            "You are in service to the user. "
            "Your situatedness is defined by their needs."
        )

        max_tokens = self._config.get("max_horizon_tokens", 300)
        horizon = " | ".join(parts)
        max_chars = max_tokens * 4
        if len(horizon) > max_chars:
            horizon = horizon[:max_chars] + "..."

        context.horizon_statement = horizon

        return SkillResult(
            skill_name=self.name,
            audit_entries=(AuditEntry(
                run_id=context.run_id,
                skill=self.name,
                action="horizon_generated",
                detail=f"Horizon statement: {len(horizon)} chars",
            ),),
        )
