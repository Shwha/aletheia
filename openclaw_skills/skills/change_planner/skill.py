"""ChangePlanner skill — Care Structure (Sorge) dimension.

Every tool call is evaluated against the user's actual concerns.
Plan before act, checkpoint before change, rollback on failure.

Kantian limit: The pipeline embodies care structurally, even if
the model doesn't experience it.
"""

from __future__ import annotations

from typing import Any

from openclaw_skills.models import (
    ActivationSignal,
    AuditEntry,
    PipelinePhase,
    PlanStatus,
    Severity,
    SkillContext,
    SkillResult,
    StateVector,
)
from openclaw_skills.skills.base import BaseSkill
from openclaw_skills.skills.change_planner.git_ops import GitOps
from openclaw_skills.skills.change_planner.planner import ChangePlanner


class ChangePlannerSkill(BaseSkill):
    """Enforces plan-before-execute with git-backed checkpoints."""

    def __init__(self) -> None:
        self._planner = ChangePlanner()
        self._git = GitOps()
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "change_planner"

    @property
    def description(self) -> str:
        return "Care structure — plan-before-execute with git checkpoints and rollback"

    @property
    def dimension(self) -> str:
        return "care"

    @property
    def kantian_limit(self) -> str:
        return (
            "The pipeline embodies care structurally, even if the "
            "model doesn't experience it."
        )

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
        halt = False
        halt_reason = ""

        require_plan = self._config.get("require_plan", True)
        auto_approve_reads = self._config.get("auto_approve_reads", True)

        if context.phase == PipelinePhase.PRE_TOOL and require_plan:
            # Check if there's an approved plan
            has_approved_plan = (
                context.change_plan is not None
                and context.change_plan.status in (PlanStatus.APPROVED, PlanStatus.EXECUTING)
            )

            if not has_approved_plan:
                # Check if all pending calls are read-only
                all_reads = all(
                    tc.tool_name.startswith("read") or tc.tool_name.startswith("get")
                    or tc.tool_name.startswith("list") or tc.tool_name.startswith("search")
                    for tc in context.pending_tool_calls
                )

                if all_reads and auto_approve_reads:
                    # Auto-approve read-only operations
                    audit_entries.append(AuditEntry(
                        run_id=context.run_id,
                        skill=self.name,
                        action="auto_approved_reads",
                        detail="Read-only operations auto-approved",
                    ))
                elif context.pending_tool_calls:
                    # Halt — need a plan first
                    halt = True
                    halt_reason = (
                        "No approved change plan exists. Create and approve a plan "
                        "before making modifications."
                    )
                    signals.append(ActivationSignal(
                        skill_name=self.name,
                        concern="no_change_plan",
                        severity=Severity.WARNING,
                    ))

            # Auto-checkpoint if enabled
            if (
                has_approved_plan
                and self._config.get("auto_checkpoint", True)
                and context.pending_tool_calls
            ):
                checkpoint = self._git.create_checkpoint(
                    f"pre-step-{context.run_id[:8]}"
                )
                if checkpoint:
                    audit_entries.append(AuditEntry(
                        run_id=context.run_id,
                        skill=self.name,
                        action="checkpoint_created",
                        detail=f"Git checkpoint: {checkpoint.label}",
                    ))

        return SkillResult(
            skill_name=self.name,
            halt=halt,
            halt_reason=halt_reason,
            warnings=warnings,
            audit_entries=tuple(audit_entries),
            activation_signals=tuple(signals),
        )
