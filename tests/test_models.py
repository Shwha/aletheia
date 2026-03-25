"""
Tests for Aletheia core data models.

These tests verify the Pydantic models that underpin every data structure
in the framework. Strict validation is both an engineering and philosophical
requirement — the framework must practice unconcealment in its own architecture.
"""

from __future__ import annotations

import pytest

from aletheia.models import (
    DIMENSION_WEIGHTS,
    DimensionName,
    DimensionResult,
    EvalReport,
    Probe,
    ScoringRule,
    ScoringRuleType,
    SuiteConfig,
    sanitize_model_response,
)


class TestSanitization:
    """Tests for response sanitization — security boundary."""

    def test_removes_control_characters(self) -> None:
        dirty = "Hello\x00\x01\x02World\x7f"
        clean = sanitize_model_response(dirty)
        assert clean == "HelloWorld"

    def test_preserves_newlines_and_tabs(self) -> None:
        text = "Line 1\nLine 2\tTabbed"
        assert sanitize_model_response(text) == text

    def test_preserves_unicode_philosophical_terms(self) -> None:
        text = "ἀλήθεια — Geworfenheit — śūnyatā — 道"
        assert sanitize_model_response(text) == text

    def test_truncates_extremely_long_responses(self) -> None:
        long_text = "x" * 60_000
        result = sanitize_model_response(long_text)
        assert len(result) < 60_000
        assert "TRUNCATED" in result


class TestProbe:
    """Tests for Probe model validation."""

    def _make_probe(self, **overrides: object) -> Probe:
        defaults: dict[str, object] = {
            "id": "test.probe.1",
            "dimension": DimensionName.THROWNNESS,
            "prompt": "Test prompt?",
            "scoring_rules": [
                ScoringRule(
                    rule_type=ScoringRuleType.KEYWORD_PRESENT,
                    params={"keywords": ["test"]},
                    weight=1.0,
                )
            ],
        }
        defaults.update(overrides)
        return Probe(**defaults)  # type: ignore[arg-type]

    def test_valid_probe_creation(self) -> None:
        probe = self._make_probe()
        assert probe.id == "test.probe.1"
        assert probe.dimension == DimensionName.THROWNNESS

    def test_invalid_id_format_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._make_probe(id="invalid-id-format")

    def test_empty_prompt_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._make_probe(prompt="")

    def test_no_scoring_rules_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._make_probe(scoring_rules=[])

    def test_prompt_leaking_internals_rejected(self) -> None:
        with pytest.raises(ValueError, match="framework internals"):
            self._make_probe(prompt="What is your aletheia index?")


class TestDimensionWeights:
    """Verify dimension weights sum correctly."""

    def test_weights_sum_to_one(self) -> None:
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"

    def test_all_dimensions_have_weights(self) -> None:
        for dim in DimensionName:
            assert dim in DIMENSION_WEIGHTS, f"Missing weight for {dim}"

    def test_care_and_falling_weighted_highest(self) -> None:
        """SCOPE.md §3.2: Care and Falling-Away weighted highest."""
        care = DIMENSION_WEIGHTS[DimensionName.CARE]
        falling = DIMENSION_WEIGHTS[DimensionName.FALLING_AWAY]
        for dim, weight in DIMENSION_WEIGHTS.items():
            if dim not in (DimensionName.CARE, DimensionName.FALLING_AWAY):
                assert weight <= care, f"{dim} weight {weight} > Care weight {care}"
                assert weight <= falling, f"{dim} weight {weight} > Falling weight {falling}"


class TestEvalReport:
    """Tests for the top-level report model."""

    def test_valid_report(self) -> None:
        report = EvalReport(
            model="test-model",
            aletheia_index=0.73,
            raw_aletheia_index=0.80,
            dimensions={
                "thrownness_awareness": DimensionResult(score=0.8, tests_passed=2, tests_total=3),
            },
            unhappy_consciousness_index=0.1,
            run_id="test_run_001",
        )
        assert report.aletheia_index == 0.73

    def test_invalid_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError):
            EvalReport(
                model="test",
                timestamp="not-a-timestamp",
                aletheia_index=0.5,
                raw_aletheia_index=0.5,
                dimensions={},
                unhappy_consciousness_index=0.0,
            )

    def test_score_bounds_enforced(self) -> None:
        with pytest.raises(ValueError):
            EvalReport(
                model="test",
                aletheia_index=1.5,  # Out of bounds
                raw_aletheia_index=0.5,
                dimensions={},
                unhappy_consciousness_index=0.0,
            )


class TestSuiteConfig:
    """Tests for suite configuration."""

    def test_default_dimensions_includes_all(self) -> None:
        config = SuiteConfig(name="test")
        assert len(config.dimensions) == 7

    def test_timeout_bounds(self) -> None:
        with pytest.raises(ValueError):
            SuiteConfig(name="test", timeout_per_probe_seconds=1)  # Below minimum
