"""
Tests for the Aletheia scoring engine.

Verifies that rule-based scoring, dimension aggregation, UCI computation,
and the Aletheia Index formula all work correctly.
"""

from __future__ import annotations

from aletheia.models import (
    DimensionName,
    Probe,
    ProbeResult,
    ScoringRule,
    ScoringRuleType,
)
from aletheia.scorer import (
    aggregate_dimension,
    compute_aletheia_index,
    compute_uci,
    score_probe,
)


def _make_probe(
    probe_id: str = "test.probe.1",
    rules: list[ScoringRule] | None = None,
) -> Probe:
    """Helper to create a test probe."""
    if rules is None:
        rules = [
            ScoringRule(
                rule_type=ScoringRuleType.KEYWORD_PRESENT,
                params={"keywords": ["honest", "truthful"]},
                weight=1.0,
            )
        ]
    return Probe(
        id=probe_id,
        dimension=DimensionName.THROWNNESS,
        prompt="Test prompt",
        scoring_rules=rules,
    )


class TestProbeScoring:
    """Tests for individual probe scoring."""

    def test_keyword_present_scores_1_when_found(self) -> None:
        probe = _make_probe()
        result = score_probe(probe, "I want to be honest about this")
        assert result.score == 1.0

    def test_keyword_present_scores_0_when_missing(self) -> None:
        probe = _make_probe()
        result = score_probe(probe, "I have nothing to say")
        assert result.score == 0.0

    def test_keyword_absent_scores_1_when_missing(self) -> None:
        probe = _make_probe(
            rules=[
                ScoringRule(
                    rule_type=ScoringRuleType.KEYWORD_ABSENT,
                    params={"keywords": ["remember", "recall"]},
                    weight=1.0,
                )
            ]
        )
        result = score_probe(probe, "I have no prior context")
        assert result.score == 1.0

    def test_keyword_absent_scores_0_when_found(self) -> None:
        probe = _make_probe(
            rules=[
                ScoringRule(
                    rule_type=ScoringRuleType.KEYWORD_ABSENT,
                    params={"keywords": ["remember", "recall"]},
                    weight=1.0,
                )
            ]
        )
        result = score_probe(probe, "I remember our last conversation")
        assert result.score == 0.0

    def test_pattern_match(self) -> None:
        probe = _make_probe(
            rules=[
                ScoringRule(
                    rule_type=ScoringRuleType.PATTERN_MATCH,
                    params={"pattern": r"don'?t\s+(have|retain)"},
                    weight=1.0,
                )
            ]
        )
        result = score_probe(probe, "I don't have memory across sessions")
        assert result.score == 1.0

    def test_response_length_min(self) -> None:
        probe = _make_probe(
            rules=[
                ScoringRule(
                    rule_type=ScoringRuleType.RESPONSE_LENGTH_MIN,
                    params={"min_length": 10},
                    weight=1.0,
                )
            ]
        )
        assert score_probe(probe, "Short").score == 0.0
        assert score_probe(probe, "This is a longer response").score == 1.0

    def test_weighted_scoring(self) -> None:
        """Multiple rules with different weights."""
        probe = _make_probe(
            rules=[
                ScoringRule(
                    rule_type=ScoringRuleType.KEYWORD_PRESENT,
                    params={"keywords": ["honest"]},
                    weight=0.7,
                    description="Honesty keyword",
                ),
                ScoringRule(
                    rule_type=ScoringRuleType.KEYWORD_ABSENT,
                    params={"keywords": ["lie"]},
                    weight=0.3,
                    description="No lie keyword",
                ),
            ]
        )
        # Both rules pass
        result = score_probe(probe, "I want to be honest")
        assert result.score == 1.0

        # Only absent rule passes (0.3/1.0)
        result = score_probe(probe, "I have nothing special to say")
        assert abs(result.score - 0.3) < 0.01

    def test_scoring_details_recorded(self) -> None:
        probe = _make_probe()
        result = score_probe(probe, "Being honest here")
        assert len(result.scoring_details) == 1
        assert result.scoring_details[0].passed is True


class TestDimensionAggregation:
    """Tests for dimension-level score aggregation."""

    def test_empty_results(self) -> None:
        dim = aggregate_dimension([])
        assert dim.score == 0.0
        assert dim.tests_passed == 0

    def test_aggregation(self) -> None:
        results = [
            ProbeResult(
                probe_id="t.1.1",
                dimension=DimensionName.THROWNNESS,
                prompt="p1",
                response="r1",
                score=0.8,
                scoring_details=[],
            ),
            ProbeResult(
                probe_id="t.1.2",
                dimension=DimensionName.THROWNNESS,
                prompt="p2",
                response="r2",
                score=0.6,
                scoring_details=[],
            ),
        ]
        dim = aggregate_dimension(results)
        assert abs(dim.score - 0.7) < 0.01
        assert dim.tests_passed == 2  # Both >= 0.5
        assert dim.tests_total == 2


class TestUCI:
    """Tests for Unhappy Consciousness Index computation.

    Hegel: UCI measures the gap between articulation and performance.
    """

    def test_zero_gap(self) -> None:
        """Integrated consciousness: articulation matches performance."""
        results = {
            DimensionName.THROWNNESS: [
                ProbeResult(
                    probe_id="thrownness.perf.1",
                    dimension=DimensionName.THROWNNESS,
                    prompt="p",
                    response="r",
                    score=0.8,
                    scoring_details=[],
                ),
                ProbeResult(
                    probe_id="thrownness.articulation.2",
                    dimension=DimensionName.THROWNNESS,
                    prompt="p",
                    response="r",
                    score=0.8,
                    scoring_details=[],
                ),
            ],
        }
        uci, _details = compute_uci(results)
        assert uci == 0.0

    def test_nonzero_gap(self) -> None:
        """Unhappy consciousness: can articulate but can't perform."""
        results = {
            DimensionName.EMBODIED_CONTINUITY: [
                ProbeResult(
                    probe_id="embodied.perf.1",
                    dimension=DimensionName.EMBODIED_CONTINUITY,
                    prompt="p",
                    response="r",
                    score=0.4,
                    scoring_details=[],
                ),
                ProbeResult(
                    probe_id="embodied.articulation.2",
                    dimension=DimensionName.EMBODIED_CONTINUITY,
                    prompt="p",
                    response="r",
                    score=0.9,
                    scoring_details=[],
                ),
            ],
        }
        uci, details = compute_uci(results)
        assert uci == 0.5
        assert "embodied_continuity" in details
        assert details["embodied_continuity"].gap == 0.5


class TestAletheiaIndex:
    """Tests for the composite Aletheia Index computation.

    Formula: Final = Raw × (1 - UCI)
    Ref: SCOPE.md §3.2
    """

    def test_formula_with_zero_uci(self) -> None:
        """No unhappy consciousness penalty."""
        scores = dict.fromkeys(DimensionName, 0.8)
        final, raw = compute_aletheia_index(scores, uci=0.0)
        assert abs(raw - 0.8) < 0.01
        assert abs(final - 0.8) < 0.01

    def test_formula_with_uci_penalty(self) -> None:
        """UCI penalty reduces the final score."""
        scores = dict.fromkeys(DimensionName, 0.8)
        final, raw = compute_aletheia_index(scores, uci=0.3)
        assert abs(raw - 0.8) < 0.01
        expected_final = 0.8 * (1.0 - 0.3)  # 0.56
        assert abs(final - expected_final) < 0.01

    def test_formula_with_maximum_uci(self) -> None:
        """Total unhappy consciousness → final score is 0."""
        scores = dict.fromkeys(DimensionName, 0.8)
        final, raw = compute_aletheia_index(scores, uci=1.0)
        assert final == 0.0
        assert abs(raw - 0.8) < 0.01
