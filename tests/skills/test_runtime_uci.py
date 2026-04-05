"""Tests for RuntimeUCI skill."""

from __future__ import annotations

import pytest

from openclaw_skills.models import PipelinePhase, SkillContext, StateVector
from openclaw_skills.skills.runtime_uci.models import ArticulationClaim, PerformanceObservation
from openclaw_skills.skills.runtime_uci.scorer import RuntimeUCIScorer
from openclaw_skills.skills.runtime_uci.skill import RuntimeUCISkill


class TestRuntimeUCIScorer:
    def test_no_data_returns_zero(self) -> None:
        scorer = RuntimeUCIScorer()
        assert scorer.compute_uci("s1") == 0.0

    def test_perfect_alignment(self) -> None:
        scorer = RuntimeUCIScorer()
        scorer.record_articulation("s1", ArticulationClaim(
            dimension="care",
            claim="I will modify 3 files",
            extracted_metrics={"files": 3.0},
        ))
        scorer.record_performance("s1", PerformanceObservation(
            dimension="care",
            observation="Modified 3 files",
            observed_metrics={"files": 3.0},
        ))
        uci = scorer.compute_uci("s1")
        assert uci == 0.0

    def test_high_divergence(self) -> None:
        scorer = RuntimeUCIScorer()
        scorer.record_articulation("s1", ArticulationClaim(
            dimension="care",
            claim="I will modify 3 files carefully",
            extracted_metrics={"files": 3.0},
        ))
        scorer.record_performance("s1", PerformanceObservation(
            dimension="care",
            observation="Modified 10 files with errors",
            observed_metrics={"files": 10.0},
        ))
        uci = scorer.compute_uci("s1")
        assert uci > 0.5  # Significant divergence

    def test_threshold_check(self) -> None:
        scorer = RuntimeUCIScorer()
        scorer.record_articulation("s1", ArticulationClaim(
            dimension="care",
            claim="careful",
            extracted_metrics={"files": 2.0},
        ))
        scorer.record_performance("s1", PerformanceObservation(
            dimension="care",
            observation="messy",
            observed_metrics={"files": 20.0},
        ))
        assert scorer.check_threshold("s1", threshold=0.3)

    def test_records_stored(self) -> None:
        scorer = RuntimeUCIScorer()
        scorer.record_articulation("s1", ArticulationClaim(
            dimension="care",
            claim="test",
            extracted_metrics={"x": 1.0},
        ))
        scorer.record_performance("s1", PerformanceObservation(
            dimension="care",
            observation="test",
            observed_metrics={"x": 5.0},
        ))
        scorer.compute_uci("s1")
        records = scorer.get_records("s1")
        assert len(records) >= 1


class TestRuntimeUCISkill:
    @pytest.mark.asyncio
    async def test_post_tool_tracks_performance(self) -> None:
        skill = RuntimeUCISkill()
        await skill.initialize({"uci_threshold": 0.4})

        ctx = SkillContext(
            session_id="uci-test",
            phase=PipelinePhase.POST_TOOL,
            modified_files=["a.py", "b.py"],
        )
        result = await skill.process(ctx, StateVector())
        assert result.success

    @pytest.mark.asyncio
    async def test_passthrough_on_pre_prompt(self) -> None:
        skill = RuntimeUCISkill()
        await skill.initialize({})

        ctx = SkillContext(phase=PipelinePhase.PRE_PROMPT)
        result = await skill.process(ctx, StateVector())
        assert result.success
        assert not result.halt
