"""InstructionCompiler skill — A Priori Articulation dimension.

Distinguishes what the model knows from training vs. what it learned
this session. Tags each directive with provenance.

Kantian limit: Cannot ensure the model internalizes the distinction
between training-knowledge and session-knowledge.
"""

from __future__ import annotations

from typing import Any

from openclaw_skills.models import (
    AuditEntry,
    PipelinePhase,
    Severity,
    SkillContext,
    SkillResult,
    StateVector,
)
from openclaw_skills.skills.base import BaseSkill
from openclaw_skills.skills.instruction_compiler.compiler import (
    compile_instructions,
    detect_ambiguity,
)


class InstructionCompilerSkill(BaseSkill):
    """Compiles complex instructions into atomic, ranked directives."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "instruction_compiler"

    @property
    def description(self) -> str:
        return "A priori articulation — compiles complex instructions into atomic directives"

    @property
    def dimension(self) -> str:
        return "a_priori"

    @property
    def kantian_limit(self) -> str:
        return (
            "Cannot ensure the model internalizes the distinction "
            "between training-knowledge and session-knowledge."
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config

    async def process(
        self,
        context: SkillContext,
        state: StateVector,
    ) -> SkillResult:
        audit_entries: list[AuditEntry] = []
        warnings: list[str] = []

        if context.phase != PipelinePhase.PRE_PROMPT:
            return SkillResult(skill_name=self.name)

        if not context.original_prompt:
            return SkillResult(skill_name=self.name)

        # Compile instructions
        instruction_set = compile_instructions(context.original_prompt)
        context.compiled_prompt = instruction_set.checklist
        context.system_instructions = [d.text for d in instruction_set.directives]

        # Check for ambiguity
        ambiguous = detect_ambiguity(context.original_prompt)
        if ambiguous:
            warnings.append(
                f"Ambiguous language detected: {', '.join(ambiguous)}. "
                "Consider making instructions more specific."
            )

        audit_entries.append(AuditEntry(
            run_id=context.run_id,
            skill=self.name,
            action="instructions_compiled",
            detail=(
                f"Compiled {len(instruction_set.directives)} directives "
                f"from {len(context.original_prompt)} chars"
            ),
        ))

        return SkillResult(
            skill_name=self.name,
            warnings=warnings,
            audit_entries=tuple(audit_entries),
        )
