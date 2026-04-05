"""HorizonFusion skill — Horizon Fusion (Gadamer) dimension.

Merges the model's context with the user's context into shared
understanding. Detects when assumptions don't align.

Kantian limit: True horizon fusion requires genuine understanding;
we approximate with structured context merging.
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


class HorizonFusionSkill(BaseSkill):
    """Merges model and user contexts, detects misalignment."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "horizon_fusion"

    @property
    def description(self) -> str:
        return "Horizon fusion — merges model and user contexts, detects misalignment"

    @property
    def dimension(self) -> str:
        return "horizon"

    @property
    def kantian_limit(self) -> str:
        return (
            "True horizon fusion requires genuine understanding; "
            "we approximate with structured context merging."
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

        signals: list[ActivationSignal] = []
        warnings: list[str] = []
        audit_entries: list[AuditEntry] = []

        # Check for misalignment signals
        if self._config.get("detect_misalignment", True):
            # High drift + high urgency = likely misalignment
            if state.drift_score > 0.5 and state.urgency > 0.5:
                warnings.append(
                    "Potential context misalignment: model is drifting from plan "
                    "while urgency is high. Consider re-establishing shared context."
                )
                signals.append(ActivationSignal(
                    skill_name=self.name,
                    concern="context_misalignment",
                    severity=Severity.WARNING,
                ))

            # Low confidence in a service context = horizon gap
            if state.confidence < 0.4 and state.relational_mode == "service":
                warnings.append(
                    "Low model confidence in service mode. The model may not "
                    "understand the user's actual needs well enough to serve them."
                )
                signals.append(ActivationSignal(
                    skill_name=self.name,
                    concern="horizon_gap",
                    severity=Severity.WARNING,
                ))

        audit_entries.append(AuditEntry(
            run_id=context.run_id,
            skill=self.name,
            action="horizon_fusion_check",
            detail=f"drift={state.drift_score:.2f} confidence={state.confidence:.2f}",
        ))

        return SkillResult(
            skill_name=self.name,
            warnings=warnings,
            audit_entries=tuple(audit_entries),
            activation_signals=tuple(signals),
        )
