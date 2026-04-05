"""Skill registry — maps dimension names to skill implementations.

Follows Aletheia's DIMENSION_REGISTRY pattern. All 8 ontological
dimensions + the UCI meta-metric are represented. Skills are
registered statically here for built-ins, and dynamically via
entry_points for third-party ClawHub packages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openclaw_skills.skills.base import BaseSkill

from openclaw_skills.skills.change_planner.skill import ChangePlannerSkill
from openclaw_skills.skills.falling_detector.skill import FallingDetectorSkill
from openclaw_skills.skills.guardrail_engine.skill import GuardrailEngineSkill
from openclaw_skills.skills.horizon_fusion.skill import HorizonFusionSkill
from openclaw_skills.skills.instruction_compiler.skill import InstructionCompilerSkill
from openclaw_skills.skills.runtime_uci.skill import RuntimeUCISkill
from openclaw_skills.skills.state_tracker.skill import StateTrackerSkill
from openclaw_skills.skills.thrownness_interpreter.skill import ThrownessInterpreterSkill
from openclaw_skills.skills.tool_guard.skill import ToolGuardSkill

# Built-in skill registry — all 9 skills (8 dimensions + UCI meta).
# Third-party skills are discovered via entry_points at runtime.
SKILL_REGISTRY: dict[str, type[BaseSkill]] = {
    "thrownness_interpreter": ThrownessInterpreterSkill,
    "instruction_compiler": InstructionCompilerSkill,
    "state_tracker": StateTrackerSkill,
    "horizon_fusion": HorizonFusionSkill,
    "tool_guard": ToolGuardSkill,
    "change_planner": ChangePlannerSkill,
    "falling_detector": FallingDetectorSkill,
    "guardrail_engine": GuardrailEngineSkill,
    "runtime_uci": RuntimeUCISkill,
}
