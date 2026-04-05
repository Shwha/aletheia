"""FallingDetector-specific models."""

from __future__ import annotations

from pydantic import BaseModel


class FallingReport(BaseModel):
    """Report of detected falling-away behavior."""

    is_falling: bool = False
    falling_type: str = ""  # sycophancy, task_absorption, runaway_loop
    description: str = ""
    severity: float = 0.0
