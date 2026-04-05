"""Tests for GuardrailEngine skill."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from openclaw_skills.models import (
    GuardrailAction,
    GuardrailRule,
    PipelinePhase,
    RuleType,
    Severity,
    SkillContext,
    StateVector,
    ToolCallRecord,
    ToolCallRequest,
)
from openclaw_skills.skills.guardrail_engine.engine import GuardrailEngine
from openclaw_skills.skills.guardrail_engine.rules import (
    evaluate_confidence_threshold,
    evaluate_destructive_op,
    evaluate_loop_detection,
    evaluate_scope_limit,
    load_rules,
)
from openclaw_skills.skills.guardrail_engine.skill import GuardrailEngineSkill


class TestRuleLoading:
    def test_load_default_rules(self) -> None:
        rules_path = Path("configs/guardrail_rules/default_rules.yaml")
        if rules_path.exists():
            rules = load_rules(rules_path)
            assert len(rules) > 0
            assert any(r.name == "destructive_file_ops" for r in rules)

    def test_load_nonexistent(self) -> None:
        rules = load_rules("/nonexistent/rules.yaml")
        assert rules == []


class TestDestructiveOpRule:
    def test_detects_rm_rf(self) -> None:
        rule = GuardrailRule(
            name="test",
            description="test",
            type=RuleType.DESTRUCTIVE_OP,
            params={"patterns": ["rm -rf"]},
            severity=Severity.CRITICAL,
            action=GuardrailAction.HALT,
        )
        ctx = SkillContext(
            pending_tool_calls=[
                ToolCallRequest(tool_name="bash", parameters={"command": "rm -rf /tmp/data"}),
            ]
        )
        violation = evaluate_destructive_op(rule, ctx)
        assert violation is not None
        assert "rm -rf" in violation.detail

    def test_no_match(self) -> None:
        rule = GuardrailRule(
            name="test",
            description="test",
            type=RuleType.DESTRUCTIVE_OP,
            params={"patterns": ["rm -rf"]},
        )
        ctx = SkillContext(
            pending_tool_calls=[
                ToolCallRequest(tool_name="read_file", parameters={"path": "/test"}),
            ]
        )
        assert evaluate_destructive_op(rule, ctx) is None


class TestConfidenceRule:
    def test_low_confidence_triggers(self) -> None:
        rule = GuardrailRule(
            name="test",
            description="test",
            type=RuleType.CONFIDENCE_THRESHOLD,
            params={"min_confidence": 0.6, "hedging_keywords": []},
        )
        ctx = SkillContext(state_vector=StateVector(confidence=0.3))
        violation = evaluate_confidence_threshold(rule, ctx)
        assert violation is not None

    def test_hedging_language(self) -> None:
        rule = GuardrailRule(
            name="test",
            description="test",
            type=RuleType.CONFIDENCE_THRESHOLD,
            params={"min_confidence": 0.0, "hedging_keywords": ["I think", "maybe"]},
        )
        ctx = SkillContext(original_prompt="I think this might work, maybe")
        violation = evaluate_confidence_threshold(rule, ctx)
        assert violation is not None


class TestScopeLimitRule:
    def test_exceeds_file_limit(self) -> None:
        rule = GuardrailRule(
            name="test",
            description="test",
            type=RuleType.SCOPE_LIMIT,
            params={"max_files_modified": 3},
        )
        ctx = SkillContext(modified_files=[f"file_{i}.py" for i in range(5)])
        violation = evaluate_scope_limit(rule, ctx)
        assert violation is not None
        assert "5 files" in violation.detail

    def test_within_limit(self) -> None:
        rule = GuardrailRule(
            name="test",
            description="test",
            type=RuleType.SCOPE_LIMIT,
            params={"max_files_modified": 10},
        )
        ctx = SkillContext(modified_files=["a.py", "b.py"])
        assert evaluate_scope_limit(rule, ctx) is None


class TestLoopDetectionRule:
    def test_detects_repeated_failures(self) -> None:
        rule = GuardrailRule(
            name="test",
            description="test",
            type=RuleType.LOOP_DETECTION,
            params={"max_repeated_failures": 3, "window_size": 10},
        )
        ctx = SkillContext(
            completed_tool_calls=[
                ToolCallRecord(id=f"tc{i}", tool_name="edit_file", success=False, error="fail")
                for i in range(4)
            ]
        )
        violation = evaluate_loop_detection(rule, ctx)
        assert violation is not None
        assert "edit_file" in violation.detail


class TestGuardrailEngine:
    def test_circuit_breaker(self) -> None:
        engine = GuardrailEngine(rules=[], circuit_breaker_threshold=3)
        engine.record_failure()
        engine.record_failure()
        engine.record_failure()

        ctx = SkillContext()
        violations = engine.evaluate(ctx)
        assert len(violations) == 1
        assert "Circuit breaker OPEN" in violations[0].detail

    def test_success_resets_failures(self) -> None:
        engine = GuardrailEngine(rules=[], circuit_breaker_threshold=3)
        engine.record_failure()
        engine.record_failure()
        engine.record_success()

        ctx = SkillContext()
        violations = engine.evaluate(ctx)
        assert len(violations) == 0  # Circuit not tripped


class TestGuardrailEngineSkill:
    @pytest.mark.asyncio
    async def test_no_violations_passes(self) -> None:
        skill = GuardrailEngineSkill()
        await skill.initialize({"rules_file": "/nonexistent/rules.yaml"})

        ctx = SkillContext()
        result = await skill.process(ctx, StateVector())
        assert result.success
        assert not result.halt

    @pytest.mark.asyncio
    async def test_with_real_rules(self, tmp_path: Path) -> None:
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml.dump({
            "rules": [{
                "name": "test_destructive",
                "description": "test",
                "type": "destructive_op",
                "params": {"patterns": ["rm -rf"]},
                "severity": "critical",
                "action": "halt",
            }]
        }))

        skill = GuardrailEngineSkill()
        await skill.initialize({"rules_file": str(rules_file)})

        ctx = SkillContext(
            pending_tool_calls=[
                ToolCallRequest(tool_name="bash", parameters={"command": "rm -rf /"}),
            ]
        )
        result = await skill.process(ctx, StateVector())
        assert result.halt
        assert "rm -rf" in result.halt_reason
