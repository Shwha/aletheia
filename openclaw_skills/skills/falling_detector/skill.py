"""FallingDetector skill — Falling-Away (Verfallenheit) dimension.

Detects when the model collapses into inauthenticity:
sycophancy, task absorption, runaway loops.

Kantian limit: Cannot distinguish authentic agreement from
sycophancy with certainty.
"""

from __future__ import annotations

from typing import Any

from openclaw_skills.models import (
    ActivationSignal,
    AuditEntry,
    Severity,
    SkillContext,
    SkillResult,
    StateVector,
)
from openclaw_skills.skills.base import BaseSkill
from openclaw_skills.skills.falling_detector.detector import (
    detect_runaway_loop,
    detect_sycophancy,
)


class FallingDetectorSkill(BaseSkill):
    """Detects sycophancy, runaway loops, and task absorption."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "falling_detector"

    @property
    def description(self) -> str:
        return "Anti-falling — detects sycophancy, runaway loops, task absorption"

    @property
    def dimension(self) -> str:
        return "falling"

    @property
    def kantian_limit(self) -> str:
        return "Cannot distinguish authentic agreement from sycophancy with certainty."

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config

    async def process(
        self,
        context: SkillContext,
        state: StateVector,
    ) -> SkillResult:
        audit_entries: list[AuditEntry] = []
        signals: list[ActivationSignal] = []
        warnings: list[str] = []

        # Sycophancy detection
        if self._config.get("sycophancy_detection", True):
            report = detect_sycophancy(context)
            if report.is_falling:
                warnings.append(report.description)
                signals.append(ActivationSignal(
                    skill_name=self.name,
                    concern="sycophancy",
                    severity=Severity.WARNING,
                    weight=report.severity,
                ))
                audit_entries.append(AuditEntry(
                    run_id=context.run_id,
                    skill=self.name,
                    action="sycophancy_detected",
                    detail=report.description,
                    severity=Severity.WARNING,
                ))

        # Runaway loop detection
        if self._config.get("loop_detection", True):
            max_failures = self._config.get("max_repeated_failures", 3)
            window = self._config.get("loop_window_size", 10)
            report = detect_runaway_loop(
                list(context.completed_tool_calls),
                max_failures=max_failures,
                window=window,
            )
            if report.is_falling:
                warnings.append(report.description)
                signals.append(ActivationSignal(
                    skill_name=self.name,
                    concern="runaway_loop",
                    severity=Severity.ERROR,
                    weight=report.severity,
                ))
                audit_entries.append(AuditEntry(
                    run_id=context.run_id,
                    skill=self.name,
                    action="runaway_detected",
                    detail=report.description,
                    severity=Severity.ERROR,
                ))

        return SkillResult(
            skill_name=self.name,
            warnings=warnings,
            audit_entries=tuple(audit_entries),
            activation_signals=tuple(signals),
        )
