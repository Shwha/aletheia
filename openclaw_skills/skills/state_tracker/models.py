"""StateTracker-specific models."""

from __future__ import annotations

from pydantic import BaseModel


class DriftReport(BaseModel):
    """Report of detected drift between plan and actual behavior."""

    is_drifting: bool = False
    drift_description: str = ""
    planned_action: str = ""
    actual_action: str = ""
    severity: float = 0.0  # 0.0 = no drift, 1.0 = complete divergence
