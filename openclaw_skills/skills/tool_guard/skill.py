"""ToolGuard skill — Unconcealment (Aletheia) dimension.

Every action is visible, traceable, honest. The audit trail IS
unconcealment — it cannot be disabled, only configured for verbosity.

Kantian limit: We enforce transparency of actions but cannot
ensure transparency of reasoning.
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
    ToolCallRecord,
)
from openclaw_skills.security import utc_now
from openclaw_skills.skills.base import BaseSkill
from openclaw_skills.skills.tool_guard.models import ToolSchema
from openclaw_skills.skills.tool_guard.rate_limiter import RateLimiter
from openclaw_skills.skills.tool_guard.validator import ToolGuardValidator


class ToolGuardSkill(BaseSkill):
    """Validates tool calls, rate-limits destructive ops, maintains audit trail."""

    def __init__(self) -> None:
        self._validator = ToolGuardValidator()
        self._rate_limiter = RateLimiter()
        self._config: dict[str, Any] = {}
        self._strict = False

    @property
    def name(self) -> str:
        return "tool_guard"

    @property
    def description(self) -> str:
        return "Unconcealment — validates tool calls, rate-limits destructive ops, audit trail"

    @property
    def dimension(self) -> str:
        return "unconcealment"

    @property
    def kantian_limit(self) -> str:
        return (
            "Enforces transparency of actions but cannot ensure "
            "transparency of reasoning."
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        self._strict = config.get("strict_mode", False)

        rate_cfg = config.get("rate_limits", {})
        self._rate_limiter = RateLimiter(
            default_per_minute=rate_cfg.get("default_per_minute", 30),
            destructive_per_minute=rate_cfg.get("destructive_per_minute", 5),
        )

    def register_tool_schema(self, schema: ToolSchema) -> None:
        """Register a tool schema for validation."""
        self._validator.register_schema(schema)

    async def process(
        self,
        context: SkillContext,
        state: StateVector,
    ) -> SkillResult:
        audit_entries: list[AuditEntry] = []
        signals: list[ActivationSignal] = []
        warnings: list[str] = []
        halt = False
        halt_reason = ""

        if context.phase != PipelinePhase.PRE_TOOL:
            return SkillResult(skill_name=self.name)

        rejected_calls: list[int] = []

        for i, call in enumerate(context.pending_tool_calls):
            # Validate against schema
            result = self._validator.validate(call, strict=self._strict)

            # Audit the validation
            audit_entries.append(AuditEntry(
                run_id=context.run_id,
                skill=self.name,
                action="tool_validated",
                detail=(
                    f"{call.tool_name}: {'PASS' if result.valid else 'FAIL'} "
                    f"errors={result.errors} warnings={result.warnings}"
                ),
                severity=Severity.INFO if result.valid else Severity.WARNING,
            ))

            if not result.valid:
                warnings.extend(result.errors)
                rejected_calls.append(i)

                signals.append(ActivationSignal(
                    skill_name=self.name,
                    concern="invalid_tool_call",
                    severity=Severity.WARNING,
                ))
                continue

            warnings.extend(result.warnings)

            # Rate limiting
            is_destructive = result.is_destructive
            if not self._rate_limiter.check(call.tool_name, is_destructive):
                warnings.append(f"Rate limit exceeded for {call.tool_name}")
                rejected_calls.append(i)

                signals.append(ActivationSignal(
                    skill_name=self.name,
                    concern="rate_limit_exceeded",
                    severity=Severity.WARNING,
                ))

                audit_entries.append(AuditEntry(
                    run_id=context.run_id,
                    skill=self.name,
                    action="rate_limited",
                    detail=f"{call.tool_name} exceeded rate limit",
                    severity=Severity.WARNING,
                ))
                continue

            # Destructive operation detection
            if is_destructive:
                signals.append(ActivationSignal(
                    skill_name=self.name,
                    concern="destructive_operation",
                    severity=Severity.ERROR,
                    weight=0.8,
                ))

                if self._config.get("dry_run", False):
                    warnings.append(
                        f"DRY RUN: {call.tool_name} would execute destructively"
                    )
                    rejected_calls.append(i)

                    audit_entries.append(AuditEntry(
                        run_id=context.run_id,
                        skill=self.name,
                        action="dry_run_blocked",
                        detail=f"Destructive tool {call.tool_name} blocked in dry-run mode",
                        severity=Severity.WARNING,
                    ))
                    continue

            # Record the call for rate limiting
            self._rate_limiter.record(call.tool_name)

        # Remove rejected calls from pending (iterate in reverse to preserve indices)
        for i in sorted(rejected_calls, reverse=True):
            if i < len(context.pending_tool_calls):
                rejected = context.pending_tool_calls.pop(i)
                context.completed_tool_calls.append(
                    ToolCallRecord(
                        id=rejected.id,
                        tool_name=rejected.tool_name,
                        parameters=rejected.parameters,
                        success=False,
                        error="Rejected by ToolGuard",
                        validated_by=self.name,
                    )
                )

        return SkillResult(
            skill_name=self.name,
            halt=halt,
            halt_reason=halt_reason,
            warnings=warnings,
            audit_entries=tuple(audit_entries),
            activation_signals=tuple(signals),
        )
