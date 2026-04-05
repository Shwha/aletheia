"""GuardrailEngine core — finitude made concrete.

Circuit breaker, scope limits, confidence thresholds, loop detection.
These are the agent's authentic acknowledgment of its own limits.
"""

from __future__ import annotations

import time

from openclaw_skills.models import (
    GuardrailAction,
    GuardrailRule,
    GuardrailViolation,
    SkillContext,
)
from openclaw_skills.skills.guardrail_engine.models import CircuitBreakerState
from openclaw_skills.skills.guardrail_engine.rules import RULE_EVALUATORS


class GuardrailEngine:
    """Evaluates all configured rules against the current context."""

    def __init__(
        self,
        rules: list[GuardrailRule] | None = None,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 300.0,
    ) -> None:
        self._rules = rules or []
        self._circuit = CircuitBreakerState(
            threshold=circuit_breaker_threshold,
            reset_timeout=circuit_breaker_timeout,
        )

    def evaluate(self, context: SkillContext) -> list[GuardrailViolation]:
        """Evaluate all rules against the context.

        Returns list of violations (may be empty).
        """
        # Check circuit breaker first
        if self._is_circuit_open():
            return [
                GuardrailViolation(
                    rule_name="circuit_breaker",
                    rule_type="circuit_breaker",
                    severity="critical",
                    action=GuardrailAction.HALT,
                    detail=(
                        f"Circuit breaker OPEN — {self._circuit.failure_count} "
                        f"failures exceeded threshold {self._circuit.threshold}. "
                        f"Resets in {self._time_until_reset():.0f}s"
                    ),
                )
            ]

        violations: list[GuardrailViolation] = []

        for rule in self._rules:
            evaluator = RULE_EVALUATORS.get(rule.type)
            if evaluator is None:
                continue

            violation = evaluator(rule, context)
            if violation is not None:
                violations.append(violation)

        return violations

    def record_failure(self) -> None:
        """Record a failure for circuit breaker tracking."""
        self._circuit.failure_count += 1
        self._circuit.last_failure_time = time.monotonic()

        if self._circuit.failure_count >= self._circuit.threshold:
            self._circuit.is_open = True
            self._circuit.opened_at = time.monotonic()

    def record_success(self) -> None:
        """Record a success — resets consecutive failure count."""
        self._circuit.failure_count = 0
        if self._circuit.is_open:
            self._circuit.is_open = False

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (tripped)."""
        if not self._circuit.is_open:
            return False

        # Check if reset timeout has elapsed
        if time.monotonic() - self._circuit.opened_at > self._circuit.reset_timeout:
            self._circuit.is_open = False
            self._circuit.failure_count = 0
            return False

        return True

    def _time_until_reset(self) -> float:
        """Time remaining until circuit breaker resets."""
        if not self._circuit.is_open:
            return 0.0
        elapsed = time.monotonic() - self._circuit.opened_at
        return max(0.0, self._circuit.reset_timeout - elapsed)

    @property
    def circuit_state(self) -> CircuitBreakerState:
        """Current circuit breaker state (read-only)."""
        return self._circuit.model_copy()
