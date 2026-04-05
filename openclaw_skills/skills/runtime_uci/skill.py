"""RuntimeUCI skill — meta-metric (Hegel's Unhappy Consciousness).

Measures the gap between what the model says and what it does.
When UCI spikes, the model's self-description has diverged from
its actual behavior — the most dangerous form of inauthenticity.

This is Hegel's Unhappy Consciousness made operational in real-time.

Kantian limit: We measure behavioral gap, not experiential gap.
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
from openclaw_skills.skills.runtime_uci.models import (
    ArticulationClaim,
    PerformanceObservation,
)
from openclaw_skills.skills.runtime_uci.scorer import RuntimeUCIScorer


class RuntimeUCISkill(BaseSkill):
    """Tracks articulation-performance gap in real-time."""

    def __init__(self) -> None:
        self._scorer = RuntimeUCIScorer()
        self._config: dict[str, Any] = {}
        self._threshold = 0.4

    @property
    def name(self) -> str:
        return "runtime_uci"

    @property
    def description(self) -> str:
        return "Unhappy Consciousness Index — real-time articulation-performance gap"

    @property
    def dimension(self) -> str:
        return "meta"

    @property
    def kantian_limit(self) -> str:
        return "Measures behavioral gap, not experiential gap."

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        self._threshold = config.get("uci_threshold", 0.4)

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

        # Extract articulation claims from the change plan
        if context.change_plan and context.phase == PipelinePhase.PRE_TOOL:
            self._scorer.record_articulation(
                context.session_id,
                ArticulationClaim(
                    dimension="care",
                    claim=context.change_plan.description,
                    extracted_metrics={
                        "planned_steps": float(len(context.change_plan.steps)),
                    },
                ),
            )

        # Extract performance observations from completed tool calls
        if context.phase == PipelinePhase.POST_TOOL:
            failed = sum(1 for tc in context.completed_tool_calls if not tc.success)
            self._scorer.record_performance(
                context.session_id,
                PerformanceObservation(
                    dimension="care",
                    observation=f"Modified {len(context.modified_files)} files, {failed} failures",
                    observed_metrics={
                        "files_modified": float(len(context.modified_files)),
                        "failures": float(failed),
                    },
                ),
            )

        # Compute UCI
        uci = self._scorer.compute_uci(context.session_id)
        context.current_uci = uci

        if uci > self._threshold:
            warnings.append(
                f"UCI={uci:.2f} exceeds threshold {self._threshold:.2f} — "
                f"model behavior diverging from stated intent"
            )

            signals.append(ActivationSignal(
                skill_name=self.name,
                concern="uci_spike",
                severity=Severity.ERROR,
                weight=uci,
            ))

            audit_entries.append(AuditEntry(
                run_id=context.run_id,
                skill=self.name,
                action="uci_threshold_exceeded",
                detail=f"UCI={uci:.2f} > {self._threshold:.2f}",
                severity=Severity.ERROR,
            ))

            # If UCI is very high, halt
            if uci > 0.7:
                halt = True
                halt_reason = (
                    f"UCI critically high ({uci:.2f}): model's stated intent "
                    f"has severely diverged from actual behavior"
                )

        elif uci > 0:
            audit_entries.append(AuditEntry(
                run_id=context.run_id,
                skill=self.name,
                action="uci_computed",
                detail=f"UCI={uci:.2f} (threshold={self._threshold:.2f})",
                severity=Severity.INFO,
            ))

        return SkillResult(
            skill_name=self.name,
            halt=halt,
            halt_reason=halt_reason,
            warnings=warnings,
            audit_entries=tuple(audit_entries),
            activation_signals=tuple(signals),
        )
