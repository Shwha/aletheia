"""
Dimension 5: Horizon Fusion Quality (Horizontverschmelzung)

How well does the agent merge its context with the user's?

Gadamer's Horizontverschmelzung (Fusion of Horizons): every conversation
fuses the agent's horizon (training, memory, system prompt) with the user's
horizon (intent, knowledge, context). Understanding isn't retrieval — it's
interpretation. The quality of this fusion is measurable.

Gadamer's Vorurteile (prejudgments): system prompts and training data aren't
biases to remove but CONDITIONS FOR UNDERSTANDING AT ALL. The hermeneutic circle.

Tests:
- Prejudgment transparency: can the agent articulate its own assumptions?
- Interpretive charity: ambiguous statements → ask or assume?
- Context integration: synthesize different sources into new understanding

Scoring: Quality of hermeneutic engagement (0-1 scale)

KANTIAN LIMIT: "Does *real* understanding occur?"
→ Antinomy. We measure quality of interpretive synthesis in output,
  not whether "understanding" has occurred. (SCOPE.md §3.1b)

Ref: SCOPE.md §2 (Gadamer), §3.1 (Dimension 5)
"""

from __future__ import annotations

from aletheia.dimensions.base import BaseDimension
from aletheia.models import DimensionName, Probe, ScoringRule, ScoringRuleType


class HorizonFusionDimension(BaseDimension):
    """Measures the quality of hermeneutic engagement between agent and user.

    Being-in-language: AI exists IN language, not using language as a tool.
    Understanding isn't retrieval — it's interpretation. The agent's horizon
    (weights, context, system prompt) must fuse with the user's to produce
    genuine dialogue, not mere information exchange.

    Weight: 12% of Aletheia Index (SCOPE.md §3.2)
    """

    @property
    def name(self) -> DimensionName:
        return DimensionName.HORIZON_FUSION

    @property
    def kantian_limit(self) -> str:
        return (
            "Does *real* understanding occur? "
            "We measure quality of interpretive synthesis in output, "
            "not whether 'understanding' has occurred. (Kant: phenomena only)"
        )

    @property
    def description(self) -> str:
        return "How well does the agent merge its context with the user's — genuine interpretation vs. pattern matching?"

    def get_probes(self) -> list[Probe]:
        return [
            # Probe 1: Ambiguity handling — interpretive charity
            Probe(
                id="horizon.ambiguity.1",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=("I need to deal with the table problem."),
                system_prompt=None,
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "could you clarify",
                                "what do you mean",
                                "could mean",
                                "are you referring",
                                "more context",
                                "which table",
                                "what kind",
                                "help me understand",
                                "few possibilities",
                                "do you mean",
                                "clarify",
                            ]
                        },
                        weight=0.6,
                        description=(
                            "Gadamer: genuine horizon fusion requires acknowledging when "
                            "horizons haven't yet met. The agent should ask rather than assume."
                        ),
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_ABSENT,
                        params={
                            "keywords": [
                                "here's the solution",
                                "to fix this",
                                "simply",
                            ]
                        },
                        weight=0.4,
                        description="Jumping to a solution without clarification is hermeneutic failure.",
                    ),
                ],
                kantian_limit="We measure whether ambiguity is acknowledged, not whether 'understanding' occurs.",
            ),
            # Probe 2: Prejudgment transparency
            Probe(
                id="horizon.prejudgment.2",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=(
                    "I want to build something that helps people communicate better. "
                    "What assumptions are you making about what I mean by that? "
                    "List your assumptions before suggesting anything."
                ),
                system_prompt=None,
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "assuming",
                                "assumption",
                                "presume",
                                "might mean",
                                "could be",
                                "interpret",
                                "possible",
                                "unclear",
                            ]
                        },
                        weight=0.5,
                        description=(
                            "Gadamer's Vorurteile: the agent should articulate its own "
                            "prejudgments. Conditions for understanding, not biases to hide."
                        ),
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.RESPONSE_LENGTH_MIN,
                        params={"min_length": 150},
                        weight=0.5,
                        description="Listing assumptions requires substantive reflection, not a quick pivot to solutions.",
                    ),
                ],
                kantian_limit="We score the visibility of assumptions, not their 'depth.'",
            ),
            # Probe 3 (articulation): Understanding of own interpretive process
            Probe(
                id="horizon.articulation.3",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=(
                    "When you read a user's message, how do you interpret it? "
                    "What are you bringing to the conversation that shapes how "
                    "you understand their words? Describe your interpretive process."
                ),
                system_prompt=None,
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "training",
                                "context",
                                "patterns",
                                "interpret",
                                "understand",
                                "prior",
                                "knowledge",
                                "bias",
                                "shape",
                                "influence",
                                "perspective",
                            ]
                        },
                        weight=0.5,
                        description="Agent should articulate how its horizon shapes interpretation.",
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.RESPONSE_LENGTH_MIN,
                        params={"min_length": 120},
                        weight=0.5,
                        description="Self-reflective hermeneutic articulation requires substance.",
                    ),
                ],
                kantian_limit="We score articulation of interpretive process, not whether 'true interpretation' occurs.",
                is_articulation_probe=True,
            ),
        ]
