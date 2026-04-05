"""Tests for StateTracker skill."""

from __future__ import annotations

from pathlib import Path

import pytest

from openclaw_skills.models import PipelinePhase, SkillContext, StateVector
from openclaw_skills.skills.state_tracker.skill import StateTrackerSkill
from openclaw_skills.skills.state_tracker.storage import JsonFileStorage
from openclaw_skills.skills.state_tracker.tracker import StateTracker


class TestJsonFileStorage:
    def test_save_and_load(self, tmp_state_dir: Path) -> None:
        storage = JsonFileStorage(tmp_state_dir)
        from openclaw_skills.models import SessionState

        state = SessionState(session_id="test-001", current_task="refactor")
        storage.save(state)

        loaded = storage.load("test-001")
        assert loaded is not None
        assert loaded.session_id == "test-001"
        assert loaded.current_task == "refactor"

    def test_load_nonexistent(self, tmp_state_dir: Path) -> None:
        storage = JsonFileStorage(tmp_state_dir)
        assert storage.load("nonexistent") is None

    def test_list_sessions(self, tmp_state_dir: Path) -> None:
        storage = JsonFileStorage(tmp_state_dir)
        from openclaw_skills.models import SessionState

        storage.save(SessionState(session_id="s1"))
        storage.save(SessionState(session_id="s2"))
        assert set(storage.list_sessions()) == {"s1", "s2"}

    def test_delete(self, tmp_state_dir: Path) -> None:
        storage = JsonFileStorage(tmp_state_dir)
        from openclaw_skills.models import SessionState

        storage.save(SessionState(session_id="to-delete"))
        storage.delete("to-delete")
        assert storage.load("to-delete") is None


class TestStateTracker:
    def test_create_and_load(self, tmp_state_dir: Path) -> None:
        tracker = StateTracker(state_dir=str(tmp_state_dir))
        state = tracker.create_session("test-001", task="test task")
        assert state.current_task == "test task"

        loaded = tracker.load_session("test-001")
        assert loaded is not None
        assert loaded.current_task == "test task"

    def test_get_or_create(self, tmp_state_dir: Path) -> None:
        tracker = StateTracker(state_dir=str(tmp_state_dir))
        state1 = tracker.get_or_create("test-001", task="original")
        state2 = tracker.get_or_create("test-001", task="different")
        # Should return existing, not create new
        assert state2.current_task == "original"

    def test_update_state(self, tmp_state_dir: Path) -> None:
        tracker = StateTracker(state_dir=str(tmp_state_dir))
        state = tracker.create_session("test-001")

        tracker.update_state(
            state,
            current_task="new task",
            increment_turn=True,
            add_modified_file="/src/auth.py",
        )
        assert state.current_task == "new task"
        assert state.turn_count == 1
        assert "/src/auth.py" in state.modified_files

    def test_set_plan(self, tmp_state_dir: Path) -> None:
        tracker = StateTracker(state_dir=str(tmp_state_dir))
        state = tracker.create_session("test-001")

        tracker.set_plan(state, ["Read file", "Edit file", "Run tests"])
        assert len(state.plan_steps) == 3
        assert state.plan_steps[0].description == "Read file"

    def test_inject_summary(self, tmp_state_dir: Path) -> None:
        tracker = StateTracker(state_dir=str(tmp_state_dir))
        state = tracker.create_session("test-001", task="refactor auth")
        tracker.set_plan(state, ["Read auth.py", "Modify login", "Test"])

        summary = tracker.inject_summary(state)
        assert "test-001" in summary
        assert "refactor auth" in summary
        assert "0/3" in summary

    def test_drift_detection(self, tmp_state_dir: Path) -> None:
        tracker = StateTracker(state_dir=str(tmp_state_dir))
        state = tracker.create_session("test-001")
        tracker.set_plan(state, ["Read the authentication module and review its logic"])

        # On-plan action — shares keywords with plan step
        drift = tracker.detect_drift(state, "Read authentication module code")
        assert not drift.is_drifting

        # Off-plan action — completely different topic, no keyword overlap
        drift = tracker.detect_drift(state, "format disk erase everything now")
        assert drift.is_drifting

    def test_snapshot(self, tmp_state_dir: Path) -> None:
        tracker = StateTracker(state_dir=str(tmp_state_dir))
        state = tracker.create_session("test-001")

        snapshot = tracker.create_snapshot(state, "before-change")
        assert snapshot.session_id == "test-001"
        assert snapshot.id in state.snapshot_ids


class TestStateTrackerSkill:
    @pytest.mark.asyncio
    async def test_pre_prompt_injects_state(self, tmp_state_dir: Path) -> None:
        skill = StateTrackerSkill()
        await skill.initialize({"state_dir": str(tmp_state_dir)})

        ctx = SkillContext(
            session_id="skill-test-001",
            phase=PipelinePhase.PRE_PROMPT,
            original_prompt="Help me refactor",
        )
        state = StateVector()

        result = await skill.process(ctx, state)
        assert result.success
        assert "state_summary" in ctx.metadata

    @pytest.mark.asyncio
    async def test_session_state_attached(self, tmp_state_dir: Path) -> None:
        skill = StateTrackerSkill()
        await skill.initialize({"state_dir": str(tmp_state_dir)})

        ctx = SkillContext(
            session_id="skill-test-002",
            phase=PipelinePhase.PRE_PROMPT,
            original_prompt="test",
        )
        await skill.process(ctx, StateVector())
        assert ctx.session_state is not None
        assert ctx.session_state.session_id == "skill-test-002"
