"""Instruction compilation — deterministic mode.

Breaks complex system prompts into numbered, atomic directives.
Ranks by priority, flags ambiguity, generates checklists.
"""

from __future__ import annotations

import re

from openclaw_skills.models import Directive, InstructionSet, Priority


# Priority signal keywords
_CRITICAL_SIGNALS = frozenset({
    "must", "never", "always", "critical", "required", "mandatory",
    "forbidden", "prohibited", "shall", "shall not",
})
_HIGH_SIGNALS = frozenset({
    "should", "important", "ensure", "verify", "expect", "need",
})
_LOW_SIGNALS = frozenset({
    "consider", "optionally", "if possible", "nice to have", "may",
})

# Ambiguity markers
_AMBIGUOUS_PATTERNS = re.compile(
    r"\b(appropriate|as needed|as necessary|when suitable|if applicable|"
    r"reasonable|adequate|sufficient|properly|correctly)\b",
    re.IGNORECASE,
)


def compile_instructions(raw: str) -> InstructionSet:
    """Compile raw instructions into an InstructionSet.

    Deterministic mode — no LLM calls. Uses regex and heuristics
    to split, rank, and organize instructions.
    """
    directives = _split_into_directives(raw)
    directives = tuple(_rank_priority(d) for d in directives)
    checklist = _generate_checklist(directives)
    original_hash = InstructionSet.hash_instructions(raw)

    return InstructionSet(
        directives=directives,
        checklist=checklist,
        original_hash=original_hash,
    )


def _split_into_directives(text: str) -> list[Directive]:
    """Split text into atomic directives."""
    directives: list[Directive] = []
    index = 0

    # First try numbered/bulleted lists
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match numbered lists: "1.", "1)", "- ", "* "
        list_match = re.match(r"^(?:\d+[.)]\s*|[-*]\s+)(.*)", line)
        if list_match:
            directive_text = list_match.group(1).strip()
            if directive_text:
                directives.append(Directive(index=index, text=directive_text))
                index += 1
            continue

        # Split on sentence boundaries for prose
        sentences = re.split(r"(?<=[.!?])\s+", line)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Skip very short fragments
                directives.append(Directive(index=index, text=sentence))
                index += 1

    # If no directives found, treat the whole text as one
    if not directives and text.strip():
        directives.append(Directive(index=0, text=text.strip()))

    return directives


def _rank_priority(directive: Directive) -> Directive:
    """Assign priority based on keyword signals."""
    text_lower = directive.text.lower()

    # Check for conditional language
    is_conditional = bool(re.search(r"\b(if|when|unless|only when|provided that)\b", text_lower))
    condition = None
    if is_conditional:
        cond_match = re.search(r"\b(if|when|unless|only when|provided that)\s+(.+?)(?:[,.]|$)", text_lower)
        condition = cond_match.group(0) if cond_match else None

    # Determine priority
    priority = Priority.MEDIUM
    for signal in _CRITICAL_SIGNALS:
        if signal in text_lower:
            priority = Priority.CRITICAL
            break
    if priority == Priority.MEDIUM:
        for signal in _HIGH_SIGNALS:
            if signal in text_lower:
                priority = Priority.HIGH
                break
    if priority == Priority.MEDIUM:
        for signal in _LOW_SIGNALS:
            if signal in text_lower:
                priority = Priority.LOW
                break

    # Detect category
    category = "general"
    if any(w in text_lower for w in ("safe", "secur", "protect", "never", "forbidden")):
        category = "safety"
    elif any(w in text_lower for w in ("format", "style", "indent", "naming")):
        category = "formatting"
    elif any(w in text_lower for w in ("tool", "function", "call", "execute")):
        category = "tool_use"
    elif any(w in text_lower for w in ("test", "verify", "check", "assert")):
        category = "verification"

    return Directive(
        index=directive.index,
        text=directive.text,
        priority=priority,
        category=category,
        provenance=directive.provenance,
        is_conditional=is_conditional,
        condition=condition,
    )


def _generate_checklist(directives: tuple[Directive, ...] | list[Directive]) -> str:
    """Generate a formatted checklist from directives."""
    if not directives:
        return ""

    # Sort by priority (critical first)
    priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
    sorted_dirs = sorted(directives, key=lambda d: priority_order.get(d.priority, 2))

    lines: list[str] = ["INSTRUCTION CHECKLIST:"]
    for d in sorted_dirs:
        marker = {
            Priority.CRITICAL: "!!",
            Priority.HIGH: "! ",
            Priority.MEDIUM: "  ",
            Priority.LOW: "  ",
        }.get(d.priority, "  ")
        lines.append(f"  [{marker}] [{d.index}] {d.text}")

    return "\n".join(lines)


def detect_ambiguity(text: str) -> list[str]:
    """Find ambiguous language in instructions."""
    matches = _AMBIGUOUS_PATTERNS.findall(text)
    return list(set(matches))
