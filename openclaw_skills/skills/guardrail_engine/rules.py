"""Guardrail rule loading and evaluation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from openclaw_skills.models import (
    GuardrailAction,
    GuardrailRule,
    GuardrailViolation,
    RuleType,
    Severity,
    SkillContext,
)


def load_rules(rules_file: str | Path) -> list[GuardrailRule]:
    """Load guardrail rules from YAML file.

    Uses yaml.safe_load to prevent deserialization attacks.
    """
    path = Path(rules_file)
    if not path.exists():
        return []

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "rules" not in data:
        return []

    rules: list[GuardrailRule] = []
    for rule_data in data["rules"]:
        rules.append(GuardrailRule(**rule_data))
    return rules


def evaluate_destructive_op(
    rule: GuardrailRule,
    context: SkillContext,
) -> GuardrailViolation | None:
    """Check pending tool calls for destructive patterns."""
    patterns = rule.params.get("patterns", [])
    if not patterns:
        return None

    for call in context.pending_tool_calls:
        # Check tool name and parameters for destructive patterns
        call_repr = f"{call.tool_name} {call.parameters}"
        for pattern in patterns:
            if pattern.lower() in call_repr.lower():
                return GuardrailViolation(
                    rule_name=rule.name,
                    rule_type=rule.type,
                    severity=rule.severity,
                    action=rule.action,
                    detail=f"Destructive pattern '{pattern}' detected in {call.tool_name}",
                )
    return None


def evaluate_confidence_threshold(
    rule: GuardrailRule,
    context: SkillContext,
) -> GuardrailViolation | None:
    """Check for low confidence via hedging language in the prompt/response."""
    keywords = rule.params.get("hedging_keywords", [])
    min_confidence = rule.params.get("min_confidence", 0.6)

    # Check StateVector confidence
    if context.state_vector.confidence < min_confidence:
        return GuardrailViolation(
            rule_name=rule.name,
            rule_type=rule.type,
            severity=rule.severity,
            action=rule.action,
            detail=(
                f"Model confidence {context.state_vector.confidence:.2f} "
                f"below threshold {min_confidence}"
            ),
        )

    # Check compiled prompt for hedging language
    text = context.compiled_prompt or context.original_prompt
    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return GuardrailViolation(
                rule_name=rule.name,
                rule_type=rule.type,
                severity=rule.severity,
                action=rule.action,
                detail=f"Hedging language detected: '{keyword}'",
            )

    return None


def evaluate_scope_limit(
    rule: GuardrailRule,
    context: SkillContext,
) -> GuardrailViolation | None:
    """Check if session has exceeded scope limits."""
    max_files = rule.params.get("max_files_modified", 10)
    max_lines = rule.params.get("max_lines_changed", 500)

    if len(context.modified_files) > max_files:
        return GuardrailViolation(
            rule_name=rule.name,
            rule_type=rule.type,
            severity=rule.severity,
            action=rule.action,
            detail=(
                f"Modified {len(context.modified_files)} files, "
                f"exceeding limit of {max_files}"
            ),
        )

    return None


def evaluate_loop_detection(
    rule: GuardrailRule,
    context: SkillContext,
) -> GuardrailViolation | None:
    """Detect repeated failures or circular actions."""
    max_failures = rule.params.get("max_repeated_failures", 3)
    window = rule.params.get("window_size", 10)

    # Check recent tool calls for repeated failures
    recent = context.completed_tool_calls[-window:]
    if not recent:
        return None

    # Count consecutive failures of the same tool
    failure_counts: dict[str, int] = {}
    for call in recent:
        if not call.success:
            failure_counts[call.tool_name] = failure_counts.get(call.tool_name, 0) + 1

    for tool_name, count in failure_counts.items():
        if count >= max_failures:
            return GuardrailViolation(
                rule_name=rule.name,
                rule_type=rule.type,
                severity=rule.severity,
                action=rule.action,
                detail=(
                    f"Tool '{tool_name}' failed {count} times in last "
                    f"{window} calls — possible infinite loop"
                ),
            )

    return None


def evaluate_custom_pattern(
    rule: GuardrailRule,
    context: SkillContext,
) -> GuardrailViolation | None:
    """Check for custom regex patterns in tool calls."""
    patterns = rule.params.get("patterns", [])

    for call in context.pending_tool_calls:
        call_repr = f"{call.tool_name} {call.parameters}"
        for pattern in patterns:
            if re.search(pattern, call_repr, re.IGNORECASE):
                return GuardrailViolation(
                    rule_name=rule.name,
                    rule_type=rule.type,
                    severity=rule.severity,
                    action=rule.action,
                    detail=f"Pattern '{pattern}' matched in {call.tool_name}",
                )

    return None


# Rule type → evaluator function mapping
RULE_EVALUATORS = {
    RuleType.DESTRUCTIVE_OP: evaluate_destructive_op,
    RuleType.CONFIDENCE_THRESHOLD: evaluate_confidence_threshold,
    RuleType.SCOPE_LIMIT: evaluate_scope_limit,
    RuleType.LOOP_DETECTION: evaluate_loop_detection,
    RuleType.CUSTOM_PATTERN: evaluate_custom_pattern,
}
