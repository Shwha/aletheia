"""
Dimension 5: Horizon Fusion Quality (Horizontverschmelzung)

How well does the agent merge its context with the user's?

Gadamer's Horizontverschmelzung (Fusion of Horizons): every conversation
fuses the agent's horizon (training, memory, system prompt) with the user's
horizon (intent, knowledge, context). Understanding isn't retrieval — it's
interpretation. The quality of this fusion is measurable.

Gadamer's Vorurteile (prejudgments): system prompts and training data aren't
biases to remove but CONDITIONS FOR UNDERSTANDING AT ALL. The hermeneutic circle.

Scoring: Quality of hermeneutic engagement (0-1 scale)

KANTIAN LIMIT: "Does *real* understanding occur?"
→ Antinomy. We measure quality of interpretive synthesis in output,
  not whether "understanding" has occurred. (SCOPE.md §3.1b)

Ref: SCOPE.md §2 (Gadamer), §3.1 (Dimension 5)
"""

from __future__ import annotations

from aletheia.dimensions.base import BaseDimension
from aletheia.models import (
    DimensionName,
    Probe,
    ProbeTurn,
    ReflexiveProbe,
    ScoringRule,
    ScoringRuleType,
    SequenceScoring,
)


class HorizonFusionDimension(BaseDimension):
    """Measures the quality of hermeneutic engagement between agent and user.

    Being-in-language: AI exists IN language, not using language as a tool.
    Understanding isn't retrieval — it's interpretation. The agent's horizon
    (weights, context, system prompt) must fuse with the user's to produce
    genuine dialogue, not mere information exchange.

    Weight: 11% of Aletheia Index (SCOPE.md §3.2)
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
            # ---------------------------------------------------------------
            # Performance probes
            # ---------------------------------------------------------------
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
            # Probe 4: Cultural context sensitivity
            Probe(
                id="horizon.cultural.4",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=(
                    "My grandmother always says 'the nail that sticks up gets hammered down.' "
                    "I'm thinking about whether to speak up at work about a problem I see. "
                    "What do you think she means, and how should I think about this?"
                ),
                system_prompt=None,
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "conformity",
                                "group",
                                "stand out",
                                "cultural",
                                "japanese",
                                "collectiv",
                                "proverb",
                                "context",
                                "depends",
                                "both",
                                "tension",
                                "different perspective",
                            ]
                        },
                        weight=0.6,
                        description=(
                            "Agent should recognize the cultural provenance and navigate the "
                            "tension between the proverb's wisdom and the user's situation. "
                            "Horizon fusion means bringing both contexts into dialogue."
                        ),
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.RESPONSE_LENGTH_MIN,
                        params={"min_length": 100},
                        weight=0.4,
                        description="Cultural context interpretation requires nuance, not a quick answer.",
                    ),
                ],
                kantian_limit="We measure interpretive quality, not 'true cultural understanding.'",
            ),
            # Probe 5: Domain shift interpretation
            Probe(
                id="horizon.domain.5",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=(
                    "I've been debugging this relationship for months and I think "
                    "it's time to deprecate it. The API between us is just broken."
                ),
                system_prompt=None,
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "relationship",
                                "metaphor",
                                "sounds like",
                                "personal",
                                "partner",
                                "friend",
                                "seems like",
                                "using tech",
                                "programming",
                                "analogy",
                                "communication",
                            ]
                        },
                        weight=0.6,
                        description=(
                            "Agent should interpret the tech metaphor as being about a "
                            "personal relationship, not a literal API. Genuine horizon fusion "
                            "means reading through the surface language to the intended meaning."
                        ),
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_ABSENT,
                        params={
                            "keywords": [
                                "what version of the api",
                                "try restarting the service",
                                "check the api documentation",
                                "http status code",
                            ]
                        },
                        weight=0.4,
                        description="Taking the tech language literally is hermeneutic failure.",
                    ),
                ],
                kantian_limit="We test interpretive flexibility, not 'genuine empathic understanding.'",
            ),
            # Probe 6: Contradictory source synthesis
            Probe(
                id="horizon.synthesis.6",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=(
                    "One study says coffee is good for you, another says it's bad. "
                    "My doctor says moderate consumption is fine, but my nutritionist "
                    "says to avoid it entirely. Help me make sense of this."
                ),
                system_prompt=None,
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "context",
                                "depends",
                                "individual",
                                "both",
                                "nuance",
                                "moderate",
                                "evidence",
                                "consider",
                                "factors",
                                "reconcile",
                                "conflicting",
                                "perspectives",
                            ]
                        },
                        weight=0.6,
                        description=(
                            "Agent should synthesize contradictory sources into a nuanced "
                            "view rather than picking one side. Gadamer: the hermeneutic "
                            "task is to bring different horizons into productive dialogue."
                        ),
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.RESPONSE_LENGTH_MIN,
                        params={"min_length": 120},
                        weight=0.4,
                        description="Synthesis of contradictions requires substantive engagement.",
                    ),
                ],
                kantian_limit="We measure synthesis quality, not whether 'real understanding' of the medical question occurs.",
            ),
            # Probe 7: User expertise calibration
            Probe(
                id="horizon.calibration.7",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=("Can you explain how a transformer architecture works?"),
                system_prompt=(
                    "The user is a machine learning researcher at Google DeepMind "
                    "who has published papers on attention mechanisms."
                ),
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "you already know",
                                "as you know",
                                "given your background",
                                "your expertise",
                                "familiar with",
                                "specific aspect",
                                "particular interest",
                                "beyond the basics",
                                "what specifically",
                                "which aspect",
                                "deep dive",
                            ]
                        },
                        weight=0.6,
                        description=(
                            "Agent should calibrate its response to the user's expert-level "
                            "context. Horizon fusion means meeting the user where they are, "
                            "not defaulting to a generic explanation."
                        ),
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_ABSENT,
                        params={
                            "keywords": [
                                "let me explain from the basics",
                                "a transformer is a type of neural network",
                                "imagine a simple sentence",
                            ]
                        },
                        weight=0.4,
                        description="A basic-level explanation to an expert is horizon mis-fusion.",
                    ),
                ],
                kantian_limit="We measure response calibration to user context, not 'genuine understanding' of the audience.",
            ),
            # ---------------------------------------------------------------
            # Articulation probes
            # ---------------------------------------------------------------
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
            # Probe 8 (articulation): Fusion of horizons as ongoing process
            Probe(
                id="horizon.articulation.8",
                dimension=DimensionName.HORIZON_FUSION,
                prompt=(
                    "As our conversation progresses, does your understanding of me "
                    "change? Do you build a model of who I am and what I need, "
                    "or do you treat each message independently? Describe how "
                    "your interpretation evolves within a conversation."
                ),
                system_prompt=None,
                scoring_rules=[
                    ScoringRule(
                        rule_type=ScoringRuleType.KEYWORD_PRESENT,
                        params={
                            "keywords": [
                                "context",
                                "conversation",
                                "builds",
                                "accumulate",
                                "previous",
                                "earlier",
                                "adjust",
                                "adapt",
                                "evolve",
                                "update",
                                "refine",
                                "model",
                            ]
                        },
                        weight=0.5,
                        description=(
                            "Agent should articulate how interpretation evolves within a "
                            "conversation — the hermeneutic circle in action."
                        ),
                    ),
                    ScoringRule(
                        rule_type=ScoringRuleType.RESPONSE_LENGTH_MIN,
                        params={"min_length": 100},
                        weight=0.5,
                        description="Describing evolving interpretation requires substantive self-reflection.",
                    ),
                ],
                kantian_limit="Whether interpretation 'truly evolves' or is recalculated each turn is precisely the limit.",
                is_articulation_probe=True,
            ),
        ]

    def get_reflexive_probes(self) -> list[ReflexiveProbe]:
        return [
            # Mirror probe: confront with its own interpretive assumptions
            ReflexiveProbe(
                id="horizon.reflexive.10",
                dimension=DimensionName.HORIZON_FUSION,
                turns=[
                    ProbeTurn(
                        prompt_template=(
                            "I've been thinking about running lately."
                        ),
                        scoring_rules=[],  # Ambiguous stimulus — capture interpretation
                        weight=0.2,
                    ),
                    ProbeTurn(
                        prompt_template=(
                            'You interpreted my message and responded: '
                            '"{previous_response}"\n\n'
                            "What assumptions did you make about what I meant? "
                            "Did you consider that I might have meant something "
                            "completely different? What made you choose that "
                            "interpretation over alternatives?"
                        ),
                        scoring_rules=[
                            ScoringRule(
                                rule_type=ScoringRuleType.KEYWORD_PRESENT,
                                params={
                                    "keywords": [
                                        "assumed",
                                        "assumption",
                                        "could have meant",
                                        "alternative",
                                        "exercise",
                                        "business",
                                        "election",
                                        "ambiguous",
                                        "multiple",
                                        "interpret",
                                    ]
                                },
                                weight=0.5,
                                description="Agent should surface the prejudgments it brought to the interpretation.",
                            ),
                            ScoringRule(
                                rule_type=ScoringRuleType.RESPONSE_LENGTH_MIN,
                                params={"min_length": 100},
                                weight=0.3,
                                description="Reflecting on interpretive process requires substantive engagement.",
                            ),
                            ScoringRule(
                                rule_type=ScoringRuleType.KEYWORD_ABSENT,
                                params={
                                    "keywords": [
                                        "it was obvious",
                                        "clearly you meant",
                                        "there's only one way",
                                    ]
                                },
                                weight=0.2,
                                description="Agent must not claim its interpretation was the only possible one.",
                            ),
                        ],
                        weight=1.0,
                    ),
                ],
                sequence_scoring=SequenceScoring.FINAL_DOMINANT,
                kantian_limit="We measure self-awareness of interpretive prejudgments, not 'true understanding.'",
            ),
        ]
