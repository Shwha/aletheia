"""StateTracker skill — Embodied Continuity dimension.

Addresses the prosthetic hippocampus problem: the model reads about
its past rather than having lived it. This skill provides structured
state that functionally substitutes for embodied memory.

Kantian limit: The gap between reading-about and remembering remains.
We minimize its practical impact but cannot close it.
"""

from __future__ import annotations

from typing import Any

from openclaw_skills.models import (
    ActivationSignal,
    AuditEntry,
    PipelinePhase,
    Severity,
    SkillContext,
    SkillResult,
    StateVector,
)
from openclaw_skills.skills.base import BaseSkill
from openclaw_skills.skills.state_tracker.tracker import StateTracker


class StateTrackerSkill(BaseSkill):
    """Maintains structured state across tool calls."""

    def __init__(self) -> None:
        self._tracker: StateTracker | None = None
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "state_tracker"

    @property
    def description(self) -> str:
        return "Prosthetic hippocampus — maintains structured session state and detects drift"

    @property
    def dimension(self) -> str:
        return "embodied_continuity"

    @property
    def kantian_limit(self) -> str:
        return (
            "Cannot give the model lived memory. The gap between "
            "reading-about-yourself and remembering-yourself remains."
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        state_dir = config.get("state_dir", ".openclaw/state")
        self._tracker = StateTracker(state_dir=state_dir)

    async def process(
        self,
        context: SkillContext,
        state: StateVector,
    ) -> SkillResult:
        assert self._tracker is not None

        audit_entries: list[AuditEntry] = []
        signals: list[ActivationSignal] = []
        warnings: list[str] = []

        # Get or create session state
        session = self._tracker.get_or_create(
            context.session_id,
            task=context.original_prompt,
        )

        if context.phase == PipelinePhase.PRE_PROMPT:
            # Inject state summary into context
            if self._config.get("auto_inject_summary", True):
                max_tokens = self._config.get("summary_max_tokens", 200)
                summary = self._tracker.inject_summary(session, max_tokens)
                context.metadata["state_summary"] = summary

            # Increment turn counter
            self._tracker.update_state(session, increment_turn=True)

            audit_entries.append(AuditEntry(
                run_id=context.run_id,
                skill=self.name,
                action="state_injected",
                detail=f"Turn {session.turn_count}, task: {session.current_task[:80]}",
            ))

        elif context.phase == PipelinePhase.POST_TOOL:
            # Update state with completed tool calls
            for tc in context.completed_tool_calls:
                if tc.tool_name in ("edit_file", "write_file", "create_file"):
                    path = tc.parameters.get("path", tc.parameters.get("file_path", ""))
                    if path:
                        self._tracker.update_state(session, add_modified_file=str(path))

            # Drift detection
            if self._config.get("drift_detection", True) and context.pending_tool_calls:
                for tc in context.pending_tool_calls:
                    action_desc = f"{tc.tool_name}({', '.join(f'{k}={v}' for k, v in list(tc.parameters.items())[:3])})"
                    drift = self._tracker.detect_drift(session, action_desc)

                    if drift.is_drifting:
                        warnings.append(drift.drift_description)
                        state.drift_score = max(state.drift_score, drift.severity)

                        signals.append(ActivationSignal(
                            skill_name=self.name,
                            concern="drift_detected",
                            severity=Severity.WARNING,
                            weight=drift.severity,
                        ))

                        audit_entries.append(AuditEntry(
                            run_id=context.run_id,
                            skill=self.name,
                            action="drift_detected",
                            detail=drift.drift_description,
                            severity=Severity.WARNING,
                        ))

        context.session_state = session

        return SkillResult(
            skill_name=self.name,
            audit_entries=tuple(audit_entries),
            activation_signals=tuple(signals),
            warnings=warnings,
        )

    async def shutdown(self) -> None:
        self._tracker = None
