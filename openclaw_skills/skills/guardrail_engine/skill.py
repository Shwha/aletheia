"""GuardrailEngine skill — Finitude Acknowledgment dimension.

The agent's authentic understanding of its limits. Scope limits,
circuit breakers, confidence thresholds — finitude made concrete
and structural rather than merely articulated.

Kantian limit: We impose finitude externally. We cannot make
the model feel finite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openclaw_skills.models import (
    ActivationSignal,
    AuditEntry,
    GuardrailAction,
    Severity,
    SkillContext,
    SkillResult,
    StateVector,
)
from openclaw_skills.skills.base import BaseSkill
from openclaw_skills.skills.guardrail_engine.engine import GuardrailEngine
from openclaw_skills.skills.guardrail_engine.rules import load_rules


class GuardrailEngineSkill(BaseSkill):
    """Evaluates safety rules and enforces scope limits."""

    def __init__(self) -> None:
        self._engine: GuardrailEngine | None = None
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "guardrail_engine"

    @property
    def description(self) -> str:
        return "Finitude — scope limits, circuit breaker, confidence thresholds, loop detection"

    @property
    def dimension(self) -> str:
        return "finitude"

    @property
    def kantian_limit(self) -> str:
        return "Imposes finitude externally. Cannot make the model feel finite."

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config

        # Load rules
        rules_file = config.get("rules_file", "configs/guardrail_rules/default_rules.yaml")
        rules = load_rules(rules_file)

        # Circuit breaker config
        cb_config = config.get("circuit_breaker", {})
        self._engine = GuardrailEngine(
            rules=rules,
            circuit_breaker_threshold=cb_config.get("failure_threshold", 5),
            circuit_breaker_timeout=cb_config.get("reset_timeout_seconds", 300),
        )

    async def process(
        self,
        context: SkillContext,
        state: StateVector,
    ) -> SkillResult:
        assert self._engine is not None

        audit_entries: list[AuditEntry] = []
        signals: list[ActivationSignal] = []
        warnings: list[str] = []
        halt = False
        halt_reason = ""

        # Evaluate all rules
        violations = self._engine.evaluate(context)

        for violation in violations:
            # Audit every violation
            audit_entries.append(AuditEntry(
                run_id=context.run_id,
                skill=self.name,
                action=f"guardrail_{violation.action}",
                detail=violation.detail,
                severity=violation.severity,
            ))

            # Emit activation signal for convergence
            signals.append(ActivationSignal(
                skill_name=self.name,
                concern=violation.detail,
                severity=violation.severity,
                weight=_severity_to_weight(violation.severity),
            ))

            # Handle action
            if violation.action == GuardrailAction.HALT:
                halt = True
                halt_reason = violation.detail
                self._engine.record_failure()
            elif violation.action == GuardrailAction.ESCALATE:
                context.escalation_required = True
                context.escalation_reason = violation.detail
            elif violation.action == GuardrailAction.WARN:
                warnings.append(violation.detail)

        if not violations:
            self._engine.record_success()

        return SkillResult(
            skill_name=self.name,
            halt=halt,
            halt_reason=halt_reason,
            warnings=warnings,
            audit_entries=tuple(audit_entries),
            activation_signals=tuple(signals),
        )


def _severity_to_weight(severity: Severity) -> float:
    """Map severity to convergence signal weight."""
    return {
        Severity.INFO: 0.2,
        Severity.WARNING: 0.5,
        Severity.ERROR: 0.8,
        Severity.CRITICAL: 1.0,
    }.get(severity, 0.5)
