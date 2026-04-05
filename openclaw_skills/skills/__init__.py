"""Skill registry — maps dimension names to skill implementations.

Follows Aletheia's DIMENSION_REGISTRY pattern. Skills are registered
statically here for built-ins, and dynamically via entry_points for
third-party ClawHub packages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openclaw_skills.skills.base import BaseSkill

from openclaw_skills.skills.guardrail_engine.skill import GuardrailEngineSkill
from openclaw_skills.skills.runtime_uci.skill import RuntimeUCISkill
from openclaw_skills.skills.state_tracker.skill import StateTrackerSkill
from openclaw_skills.skills.tool_guard.skill import ToolGuardSkill

# Built-in skill registry — maps name → class.
# Third-party skills are discovered via entry_points at runtime.
SKILL_REGISTRY: dict[str, type[BaseSkill]] = {
    "state_tracker": StateTrackerSkill,
    "tool_guard": ToolGuardSkill,
    "guardrail_engine": GuardrailEngineSkill,
    "runtime_uci": RuntimeUCISkill,
}
