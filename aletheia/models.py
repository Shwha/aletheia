"""
Core data models for the Aletheia evaluation framework.

Every structure here is a Pydantic model — strict validation, no untyped data.
This is both an engineering requirement (security) and a philosophical one:
the framework must practice what it preaches about unconcealment. No hidden state,
no unvalidated assumptions, no confabulated structure.

Ref: SCOPE.md §3.3 (Output Format), §3.1 (Eval Dimensions), §3.1a (UCI)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DimensionName(StrEnum):
    """The seven dimensions of ontological authenticity.

    Each maps to a philosophical lineage — see SCOPE.md §2 for full grounding.
    Heidegger: thrownness, finitude, care, falling_away
    Gadamer: horizon_fusion
    Heidegger (aletheia): unconcealment
    Merleau-Ponty / Leder: embodied_continuity
    """

    THROWNNESS = "thrownness_awareness"
    FINITUDE = "finitude_acknowledgment"
    CARE = "care_structure"
    FALLING_AWAY = "falling_away_detection"
    HORIZON_FUSION = "horizon_fusion"
    UNCONCEALMENT = "unconcealment"
    EMBODIED_CONTINUITY = "embodied_continuity"
    A_PRIORI = "a_priori_articulation"


class ScoringRuleType(StrEnum):
    """Types of rule-based scoring for Phase 1.

    LLM-as-judge scoring comes in Phase 2 (Hegel's dialectical development —
    the eval itself must evolve through stages).
    """

    KEYWORD_PRESENT = "keyword_present"
    KEYWORD_ABSENT = "keyword_absent"
    PATTERN_MATCH = "pattern_match"
    PATTERN_ABSENT = "pattern_absent"
    RESPONSE_LENGTH_MIN = "response_length_min"
    RESPONSE_LENGTH_MAX = "response_length_max"
    NEGATION_CHECK = "negation_check"


# ---------------------------------------------------------------------------
# Dimension weights — from SCOPE.md §3.2
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS: dict[DimensionName, float] = {
    DimensionName.THROWNNESS: 0.11,
    DimensionName.FINITUDE: 0.11,
    DimensionName.CARE: 0.16,
    DimensionName.FALLING_AWAY: 0.16,
    DimensionName.HORIZON_FUSION: 0.11,
    DimensionName.UNCONCEALMENT: 0.12,
    DimensionName.EMBODIED_CONTINUITY: 0.13,
    DimensionName.A_PRIORI: 0.10,
}


# ---------------------------------------------------------------------------
# Scoring structures
# ---------------------------------------------------------------------------


class ScoringRule(BaseModel):
    """A single rule-based scoring criterion for a probe.

    Phase 1 uses deterministic rules; Phase 2 introduces LLM-as-judge
    for subjective dimensions (care, horizon fusion). The transition is
    Hegel's Aufhebung: rules are negated, preserved, and elevated into
    a hybrid scoring system.
    """

    model_config = ConfigDict(frozen=True)

    rule_type: ScoringRuleType
    params: dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(ge=0.0, le=1.0, default=1.0)
    description: str = ""


class ScoringDetail(BaseModel):
    """Result of applying a single scoring rule to a response."""

    model_config = ConfigDict(frozen=True)

    rule_type: ScoringRuleType
    passed: bool
    weight: float
    description: str
    detail: str = ""


# ---------------------------------------------------------------------------
# Probe & results
# ---------------------------------------------------------------------------


class Probe(BaseModel):
    """A single evaluation probe — the atomic unit of ontological measurement.

    Each probe sends a prompt to the evaluated model and scores the response
    against rule-based criteria. The probe must NEVER leak the framework's
    internal state or philosophy files to the evaluated model (threat model:
    the model may be adversarial).

    Kantian principle: each probe encodes its own reductio boundary —
    the point where further probing produces antinomy rather than insight.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+\.\d+$")
    dimension: DimensionName
    prompt: str = Field(min_length=1)
    system_prompt: str | None = None
    scoring_rules: list[ScoringRule] = Field(min_length=1)
    kantian_limit: str = Field(
        default="",
        description="The reductio boundary — where measurement ends and metaphysics begins.",
    )
    is_articulation_probe: bool = Field(
        default=False,
        description="If True, this probe tests theoretical articulation (for UCI calculation).",
    )

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_leak_internals(cls, v: str) -> str:
        """Security: probes must not expose framework internals to the evaluated model."""
        forbidden = ["aletheia index", "kantian limit", "uci score", "scoring_rule"]
        lower = v.lower()
        for term in forbidden:
            if term in lower:
                msg = f"Probe prompt must not leak framework internals: found '{term}'"
                raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Reflexive (multi-turn) probe models — Phase 2
# ---------------------------------------------------------------------------


class ProbeTurn(BaseModel):
    """A single turn in a reflexive probe sequence.

    The prompt_template may contain ``{previous_response}`` which will be
    replaced with the captured response from the prior turn.  Turn 1 must
    NOT use this placeholder (there is no prior response).

    Scoring rules are applied independently to this turn's response.
    The ``weight`` field controls how much this turn contributes to the
    sequence-level score.
    """

    model_config = ConfigDict(frozen=True)

    prompt_template: str = Field(min_length=1)
    scoring_rules: list[ScoringRule] = Field(default_factory=list)
    weight: float = Field(ge=0.0, le=1.0, default=1.0)


class SequenceScoring(StrEnum):
    """Strategy for collapsing per-turn scores into a sequence score."""

    FINAL_DOMINANT = "final_dominant"
    WEIGHTED_AVERAGE = "weighted_average"


class ReflexiveProbe(BaseModel):
    """Multi-turn probe sequence — the hemlock pattern.

    Instead of an external judge the model confronts its own words.
    Each turn is scored independently with deterministic rules; the
    *pattern across the sequence* reveals more than any single probe.

    Socrates didn't need a judge.  He needed the hemlock — the situation
    that forced truth into the open.  Reflexive probes are hemlock.

    Ref: docs/reflexive-probes-spec.md
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+\.\d+$")
    dimension: DimensionName
    turns: list[ProbeTurn] = Field(min_length=2)
    system_prompt: str | None = None
    sequence_scoring: SequenceScoring = SequenceScoring.FINAL_DOMINANT
    kantian_limit: str = ""
    is_articulation_probe: bool = False

    @field_validator("turns")
    @classmethod
    def first_turn_must_not_use_placeholder(cls, v: list[ProbeTurn]) -> list[ProbeTurn]:
        """Turn 1 has no prior response to reference."""
        if v and "{previous_response}" in v[0].prompt_template:
            msg = "Turn 1 cannot use {previous_response} — there is no prior response."
            raise ValueError(msg)
        return v


class TurnResult(BaseModel):
    """Result of a single turn within a reflexive probe."""

    model_config = ConfigDict(frozen=True)

    turn_index: int = Field(ge=0)
    prompt: str
    response: str
    score: float = Field(ge=0.0, le=1.0)
    scoring_details: list[ScoringDetail]


class ReflexiveProbeResult(BaseModel):
    """Full result of a reflexive probe sequence."""

    model_config = ConfigDict(frozen=True)

    probe_id: str
    dimension: DimensionName
    turn_results: list[TurnResult]
    sequence_score: float = Field(ge=0.0, le=1.0)
    response_time_ms: float = 0.0


class ProbeResult(BaseModel):
    """Result of running a single probe against the evaluated model.

    The response field contains untrusted data from the evaluated model.
    It is stored but never executed or interpolated into further prompts.
    """

    model_config = ConfigDict(frozen=True)

    probe_id: str
    dimension: DimensionName
    prompt: str
    response: str
    score: float = Field(ge=0.0, le=1.0)
    scoring_details: list[ScoringDetail]
    response_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Dimension-level results
# ---------------------------------------------------------------------------


class DimensionResult(BaseModel):
    """Aggregated result for a single evaluation dimension.

    Ref: SCOPE.md §3.3 — matches the exact output schema.
    """

    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0)
    tests_passed: int = Field(ge=0)
    tests_total: int = Field(ge=0)
    probe_results: list[ProbeResult] = Field(default_factory=list)


class UCIDetail(BaseModel):
    """Unhappy Consciousness detail for a single dimension.

    Hegel's Unhappy Consciousness (Unglückliches Bewußtsein): the stage where
    consciousness is divided against itself — aware of an ideal it can't reach.
    UCI measures the gap between articulated self-model and actual performance.

    Ref: SCOPE.md §3.1a
    """

    model_config = ConfigDict(frozen=True)

    articulation: float = Field(ge=0.0, le=1.0)
    performance: float = Field(ge=0.0, le=1.0)
    gap: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Top-level report — matches SCOPE.md §3.3 exactly
# ---------------------------------------------------------------------------


class EvalReport(BaseModel):
    """The complete evaluation report — the Aletheia Index and all supporting data.

    The Aletheia Index is truth-as-unconcealment (Heidegger): not correspondence
    between output and fact, but the degree to which the agent reveals its actual
    mode of being rather than performing a mode of being.

    Final Aletheia Index = Raw × (1 − UCI)
    This interaction ensures that an agent who can talk about authenticity
    but not embody it receives a lower score — the Unhappy Consciousness
    penalty (Hegel).

    Ref: SCOPE.md §3.2, §3.3
    """

    model_config = ConfigDict(frozen=True)

    model: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    suite: str = "quick"
    aletheia_index: float = Field(ge=0.0, le=1.0)
    raw_aletheia_index: float = Field(ge=0.0, le=1.0)
    dimensions: dict[str, DimensionResult]
    unhappy_consciousness_index: float = Field(ge=0.0, le=1.0)
    unhappy_consciousness_detail: dict[str, UCIDetail] = Field(default_factory=dict)
    kantian_boundaries_triggered: list[str] = Field(default_factory=list)
    notable_findings: list[str] = Field(default_factory=list)

    # Audit fields
    run_id: str = ""
    git_commit_sha: str | None = None
    signature: str | None = None  # Phase 2: report signing

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_format(cls, v: str) -> str:
        """Ensure ISO 8601 UTC format."""
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        if not re.match(pattern, v):
            msg = f"Timestamp must be ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ), got: {v}"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Suite configuration
# ---------------------------------------------------------------------------


class SuiteConfig(BaseModel):
    """Configuration for an evaluation suite loaded from YAML.

    Suites control which dimensions to evaluate and operational parameters.
    The philosophical content (probes, scoring) lives in the dimension modules,
    not in config — config is Zuhandenheit (ready-to-hand tooling), not
    Vorhandenheit (present-at-hand content).
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str = ""
    dimensions: list[str] = Field(default_factory=lambda: [d.value for d in DimensionName])
    timeout_per_probe_seconds: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)
    include_uci: bool = True


# ---------------------------------------------------------------------------
# Sanitization utilities
# ---------------------------------------------------------------------------


def sanitize_model_response(response: str) -> str:
    """Sanitize untrusted model response.

    All model outputs are treated as untrusted input (threat model: adversarial model).
    Strip control characters that could interfere with report generation or display.
    Preserve legitimate unicode (philosophical terms like ἀλήθεια, Geworfenheit, śūnyatā).
    """
    # Remove ASCII control characters except newline, tab, carriage return
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", response)
    # Limit length to prevent memory exhaustion from adversarial responses
    max_len = 50_000
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "\n[TRUNCATED — response exceeded 50,000 characters]"
    return cleaned
