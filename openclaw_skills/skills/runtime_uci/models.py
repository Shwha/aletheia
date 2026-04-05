"""RuntimeUCI-specific models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArticulationClaim(BaseModel):
    """Something the model said it would do."""

    dimension: str
    claim: str
    extracted_metrics: dict[str, float] = Field(default_factory=dict)
    # e.g., {"files_to_modify": 3, "careful": 1.0}


class PerformanceObservation(BaseModel):
    """Something the model actually did."""

    dimension: str
    observation: str
    observed_metrics: dict[str, float] = Field(default_factory=dict)
    # e.g., {"files_modified": 10, "errors": 2}
