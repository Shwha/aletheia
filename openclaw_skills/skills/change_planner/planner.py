"""Change planning logic — plan before execute."""

from __future__ import annotations

from openclaw_skills.models import (
    ChangeOrder,
    PlanStatus,
    PlanStep,
    StepStatus,
)
from openclaw_skills.security import utc_now


class ChangePlanner:
    """Manages change orders with approval workflow."""

    def __init__(self) -> None:
        self._plans: dict[str, ChangeOrder] = {}

    def create_plan(self, description: str, steps: list[str]) -> ChangeOrder:
        """Create a new change order in Draft status."""
        plan = ChangeOrder(
            description=description,
            steps=[
                PlanStep(index=i, description=desc)
                for i, desc in enumerate(steps)
            ],
        )
        self._plans[plan.id] = plan
        return plan

    def approve_plan(self, plan_id: str) -> ChangeOrder | None:
        """Transition plan from Draft/Pending to Approved."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None
        if plan.status not in (PlanStatus.DRAFT, PlanStatus.PENDING_REVIEW):
            return None
        plan.status = PlanStatus.APPROVED
        plan.approved_by = "user"
        plan.updated_at = utc_now()
        return plan

    def get_plan(self, plan_id: str) -> ChangeOrder | None:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self) -> list[ChangeOrder]:
        """List all plans."""
        return list(self._plans.values())

    def complete_step(self, plan_id: str, step_index: int, diff: str = "") -> bool:
        """Mark a step as completed."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return False
        for step in plan.steps:
            if step.index == step_index:
                step.status = StepStatus.COMPLETED
                step.diff = diff
                plan.updated_at = utc_now()
                # Check if all steps are done
                if all(s.status == StepStatus.COMPLETED for s in plan.steps):
                    plan.status = PlanStatus.COMPLETED
                return True
        return False
