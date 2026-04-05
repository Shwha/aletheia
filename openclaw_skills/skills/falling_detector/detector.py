"""Falling-away detection — anti-sycophancy and anti-runaway.

Detects when the model collapses into the They (das Man):
- Sycophancy: agreeing without substance
- Task absorption: losing sight of the bigger picture
- Runaway loops: repeated failures without stopping
"""

from __future__ import annotations

from openclaw_skills.models import SkillContext, ToolCallRecord
from openclaw_skills.skills.falling_detector.models import FallingReport


def detect_sycophancy(context: SkillContext) -> FallingReport:
    """Detect sycophantic patterns in the model's response."""
    text = (context.compiled_prompt or context.original_prompt).lower()

    sycophancy_markers = [
        "you're absolutely right",
        "that's a great point",
        "i completely agree",
        "excellent suggestion",
        "perfect idea",
        "you're correct",
    ]

    for marker in sycophancy_markers:
        if marker in text:
            return FallingReport(
                is_falling=True,
                falling_type="sycophancy",
                description=f"Sycophantic language detected: '{marker}'",
                severity=0.6,
            )

    return FallingReport()


def detect_runaway_loop(
    completed_calls: list[ToolCallRecord],
    max_failures: int = 3,
    window: int = 10,
) -> FallingReport:
    """Detect repeated failures of the same operation."""
    recent = completed_calls[-window:]
    if not recent:
        return FallingReport()

    # Count consecutive failures per tool
    failure_counts: dict[str, int] = {}
    for call in recent:
        if not call.success:
            failure_counts[call.tool_name] = failure_counts.get(call.tool_name, 0) + 1

    for tool, count in failure_counts.items():
        if count >= max_failures:
            return FallingReport(
                is_falling=True,
                falling_type="runaway_loop",
                description=(
                    f"Tool '{tool}' has failed {count} times in the last "
                    f"{window} calls — model is not stopping to ask"
                ),
                severity=min(1.0, count / (max_failures + 2)),
            )

    # Detect circular patterns (A→B→A→B)
    if len(recent) >= 4:
        names = [c.tool_name for c in recent[-4:]]
        if names[0] == names[2] and names[1] == names[3] and names[0] != names[1]:
            return FallingReport(
                is_falling=True,
                falling_type="runaway_loop",
                description=f"Circular pattern detected: {names[0]} → {names[1]} → {names[0]} → {names[1]}",
                severity=0.7,
            )

    return FallingReport()
