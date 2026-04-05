"""Tests for ToolGuard skill."""

from __future__ import annotations

import pytest

from openclaw_skills.models import PipelinePhase, SkillContext, StateVector, ToolCallRequest
from openclaw_skills.skills.tool_guard.models import ParameterSchema, ToolSchema, ValidationResult
from openclaw_skills.skills.tool_guard.rate_limiter import RateLimiter
from openclaw_skills.skills.tool_guard.skill import ToolGuardSkill
from openclaw_skills.skills.tool_guard.validator import ToolGuardValidator


class TestToolGuardValidator:
    def test_unregistered_permissive(self) -> None:
        v = ToolGuardValidator()
        call = ToolCallRequest(tool_name="unknown", parameters={})
        result = v.validate(call, strict=False)
        assert result.valid

    def test_unregistered_strict(self) -> None:
        v = ToolGuardValidator()
        call = ToolCallRequest(tool_name="unknown", parameters={})
        result = v.validate(call, strict=True)
        assert not result.valid

    def test_valid_call(self) -> None:
        v = ToolGuardValidator()
        v.register_schema(ToolSchema(
            name="read_file",
            parameters={"path": ParameterSchema(type="string", required=True)},
        ))
        call = ToolCallRequest(tool_name="read_file", parameters={"path": "/test.py"})
        result = v.validate(call)
        assert result.valid

    def test_missing_required_param(self) -> None:
        v = ToolGuardValidator()
        v.register_schema(ToolSchema(
            name="read_file",
            parameters={"path": ParameterSchema(type="string", required=True)},
        ))
        call = ToolCallRequest(tool_name="read_file", parameters={})
        result = v.validate(call)
        assert not result.valid
        assert any("Missing required" in e for e in result.errors)

    def test_wrong_type(self) -> None:
        v = ToolGuardValidator()
        v.register_schema(ToolSchema(
            name="seek",
            parameters={"offset": ParameterSchema(type="integer", required=True)},
        ))
        call = ToolCallRequest(tool_name="seek", parameters={"offset": "not_a_number"})
        result = v.validate(call)
        assert not result.valid

    def test_enum_validation(self) -> None:
        v = ToolGuardValidator()
        v.register_schema(ToolSchema(
            name="set_mode",
            parameters={"mode": ParameterSchema(type="enum", enum_values=["read", "write"])},
        ))
        call = ToolCallRequest(tool_name="set_mode", parameters={"mode": "delete"})
        result = v.validate(call)
        assert not result.valid

    def test_range_validation(self) -> None:
        v = ToolGuardValidator()
        v.register_schema(ToolSchema(
            name="set_level",
            parameters={"level": ParameterSchema(type="integer", min_value=0, max_value=10)},
        ))
        call = ToolCallRequest(tool_name="set_level", parameters={"level": 15})
        result = v.validate(call)
        assert not result.valid

    def test_destructive_flag(self) -> None:
        v = ToolGuardValidator()
        v.register_schema(ToolSchema(name="delete_file", destructive=True))
        assert v.is_destructive("delete_file")
        assert not v.is_destructive("read_file")


class TestRateLimiter:
    def test_allows_under_limit(self) -> None:
        rl = RateLimiter(default_per_minute=5)
        for _ in range(4):
            assert rl.check("test")
            rl.record("test")

    def test_blocks_over_limit(self) -> None:
        rl = RateLimiter(default_per_minute=3)
        for _ in range(3):
            rl.record("test")
        assert not rl.check("test")

    def test_destructive_lower_limit(self) -> None:
        rl = RateLimiter(default_per_minute=30, destructive_per_minute=2)
        rl.record("delete")
        rl.record("delete")
        assert not rl.check("delete", is_destructive=True)
        assert rl.check("delete", is_destructive=False)  # Normal limit not hit

    def test_reset(self) -> None:
        rl = RateLimiter(default_per_minute=1)
        rl.record("test")
        assert not rl.check("test")
        rl.reset()
        assert rl.check("test")


class TestToolGuardSkill:
    @pytest.mark.asyncio
    async def test_pre_tool_validates(self) -> None:
        skill = ToolGuardSkill()
        await skill.initialize({"strict_mode": False})

        ctx = SkillContext(
            phase=PipelinePhase.PRE_TOOL,
            pending_tool_calls=[
                ToolCallRequest(tool_name="read_file", parameters={"path": "/test"}),
            ],
        )
        result = await skill.process(ctx, StateVector())
        assert result.success
        assert not result.halt

    @pytest.mark.asyncio
    async def test_non_pre_tool_passthrough(self) -> None:
        skill = ToolGuardSkill()
        await skill.initialize({})

        ctx = SkillContext(phase=PipelinePhase.PRE_PROMPT)
        result = await skill.process(ctx, StateVector())
        assert result.success

    @pytest.mark.asyncio
    async def test_strict_rejects_unregistered(self) -> None:
        skill = ToolGuardSkill()
        await skill.initialize({"strict_mode": True})

        ctx = SkillContext(
            phase=PipelinePhase.PRE_TOOL,
            pending_tool_calls=[
                ToolCallRequest(tool_name="unknown_tool", parameters={}),
            ],
        )
        result = await skill.process(ctx, StateVector())
        # Should have rejected the call
        assert len(ctx.pending_tool_calls) == 0
        assert len(ctx.completed_tool_calls) == 1
        assert not ctx.completed_tool_calls[0].success
