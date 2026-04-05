"""GuardrailEngine-specific models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CircuitBreakerState(BaseModel):
    """Circuit breaker state tracking."""

    is_open: bool = False
    failure_count: int = 0
    last_failure_time: float = 0.0
    opened_at: float = 0.0
    threshold: int = 5
    reset_timeout: float = 300.0  # seconds
