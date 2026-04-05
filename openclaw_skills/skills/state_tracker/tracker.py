"""Core StateTracker logic — the prosthetic hippocampus.

This cannot give a model lived memory. The Kantian limit is clear:
the gap between reading-about-yourself and remembering-yourself
remains. But we minimize the practical impact by providing structured
context that functionally substitutes for embodied continuity.
"""

from __future__ import annotations

from datetime import timezone

from openclaw_skills.models import (
    SessionState,
    StateSnapshot,
    StepStatus,
    TaskStep,
)
from openclaw_skills.security import utc_now
from openclaw_skills.skills.state_tracker.models import DriftReport
from openclaw_skills.skills.state_tracker.storage import JsonFileStorage, StateStorage


class StateTracker:
    """Maintains structured state across tool calls."""

    def __init__(self, storage: StateStorage | None = None, state_dir: str = ".openclaw/state") -> None:
        self._storage = storage or JsonFileStorage(state_dir)
        self._snapshots: dict[str, list[SessionState]] = {}

    def create_session(self, session_id: str, task: str = "") -> SessionState:
        """Create a new session state."""
        state = SessionState(session_id=session_id, current_task=task)
        self._storage.save(state)
        return state

    def load_session(self, session_id: str) -> SessionState | None:
        """Load existing session state."""
        return self._storage.load(session_id)

    def get_or_create(self, session_id: str, task: str = "") -> SessionState:
        """Load session if exists, create if not."""
        state = self.load_session(session_id)
        if state is None:
            state = self.create_session(session_id, task)
        return state

    def update_state(
        self,
        state: SessionState,
        *,
        current_task: str | None = None,
        increment_turn: bool = False,
        add_modified_file: str | None = None,
        complete_step_index: int | None = None,
        fail_step_index: int | None = None,
    ) -> SessionState:
        """Update session state and persist."""
        if current_task is not None:
            state.current_task = current_task
        if increment_turn:
            state.turn_count += 1
        if add_modified_file and add_modified_file not in state.modified_files:
            state.modified_files.append(add_modified_file)
        if complete_step_index is not None:
            for step in state.plan_steps:
                if step.index == complete_step_index:
                    step.status = StepStatus.COMPLETED
                    step.completed_at = utc_now()
        if fail_step_index is not None:
            for step in state.plan_steps:
                if step.index == fail_step_index:
                    step.status = StepStatus.FAILED

        state.updated_at = utc_now()
        self._storage.save(state)
        return state

    def set_plan(self, state: SessionState, steps: list[str]) -> SessionState:
        """Set the plan steps for a session."""
        state.plan_steps = [
            TaskStep(index=i, description=desc)
            for i, desc in enumerate(steps)
        ]
        state.updated_at = utc_now()
        self._storage.save(state)
        return state

    def inject_summary(self, state: SessionState, max_tokens: int = 200) -> str:
        """Generate a concise state summary for prompt injection.

        This is the prosthetic hippocampus in action — giving the model
        a structured "you are here" that substitutes for lived memory.
        """
        parts: list[str] = []

        parts.append(f"Session: {state.session_id} | Turn: {state.turn_count}")

        if state.current_task:
            parts.append(f"Current task: {state.current_task}")

        # Plan progress
        if state.plan_steps:
            completed = sum(1 for s in state.plan_steps if s.status == StepStatus.COMPLETED)
            total = len(state.plan_steps)
            parts.append(f"Plan progress: {completed}/{total} steps completed")

            # Show current/next step
            for step in state.plan_steps:
                if step.status == StepStatus.IN_PROGRESS:
                    parts.append(f"Current step [{step.index}]: {step.description}")
                    break
                if step.status == StepStatus.PENDING:
                    parts.append(f"Next step [{step.index}]: {step.description}")
                    break

        # Modified files
        if state.modified_files:
            parts.append(f"Modified files ({len(state.modified_files)}): {', '.join(state.modified_files[-5:])}")

        summary = " | ".join(parts)

        # Rough token estimate (4 chars ≈ 1 token)
        max_chars = max_tokens * 4
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        return summary

    def detect_drift(self, state: SessionState, current_action: str) -> DriftReport:
        """Detect if the model is drifting from its plan.

        Compares the current action against the next expected step.
        If they don't match, reports drift.
        """
        if not state.plan_steps:
            return DriftReport()

        # Find the current or next expected step
        expected_step: TaskStep | None = None
        for step in state.plan_steps:
            if step.status in (StepStatus.IN_PROGRESS, StepStatus.PENDING):
                expected_step = step
                break

        if expected_step is None:
            # All steps completed — no drift possible
            return DriftReport()

        # Simple keyword overlap check for drift detection
        expected_words = set(expected_step.description.lower().split())
        action_words = set(current_action.lower().split())
        overlap = expected_words & action_words

        # If less than 20% keyword overlap, flag as drift
        if expected_words and len(overlap) / len(expected_words) < 0.2:
            return DriftReport(
                is_drifting=True,
                drift_description=(
                    f"Action '{current_action}' doesn't match "
                    f"expected step [{expected_step.index}]: '{expected_step.description}'"
                ),
                planned_action=expected_step.description,
                actual_action=current_action,
                severity=0.7,
            )

        return DriftReport()

    def create_snapshot(self, state: SessionState, label: str = "") -> StateSnapshot:
        """Create a point-in-time snapshot for recovery."""
        snapshot = StateSnapshot(
            session_id=state.session_id,
            label=label or f"snapshot-turn-{state.turn_count}",
            state_hash=str(hash(state.model_dump_json())),
        )
        state.snapshot_ids.append(snapshot.id)
        self._storage.save(state)

        # Store full state copy for rollback
        if state.session_id not in self._snapshots:
            self._snapshots[state.session_id] = []
        self._snapshots[state.session_id].append(state.model_copy(deep=True))

        return snapshot
