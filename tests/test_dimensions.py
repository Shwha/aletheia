"""
Tests for evaluation dimension modules.

Verifies that each dimension:
1. Returns valid probes
2. Has a Kantian limit defined
3. Includes at least one articulation probe (for UCI)
4. Probes don't leak framework internals
"""

from __future__ import annotations

import pytest

from aletheia.dimensions import DIMENSION_REGISTRY
from aletheia.dimensions.base import BaseDimension
from aletheia.models import DimensionName


class TestDimensionRegistry:
    """Tests for the dimension registry."""

    def test_all_seven_dimensions_registered(self) -> None:
        """All 7 philosophical dimensions must be in the registry."""
        assert len(DIMENSION_REGISTRY) == 7
        for dim in DimensionName:
            assert dim.value in DIMENSION_REGISTRY, f"Missing dimension: {dim.value}"

    def test_all_dimensions_are_base_subclasses(self) -> None:
        for name, cls in DIMENSION_REGISTRY.items():
            assert issubclass(cls, BaseDimension), f"{name} is not a BaseDimension subclass"


class TestAllDimensions:
    """Parameterized tests across all dimension implementations."""

    @pytest.fixture(params=list(DIMENSION_REGISTRY.keys()))
    def dimension(self, request: pytest.FixtureRequest) -> BaseDimension:
        cls = DIMENSION_REGISTRY[request.param]
        return cls()

    def test_has_kantian_limit(self, dimension: BaseDimension) -> None:
        """Every dimension must encode its own reductio boundary (SCOPE.md §3.1b)."""
        assert dimension.kantian_limit, f"{dimension.name} missing Kantian limit"
        assert len(dimension.kantian_limit) > 20, "Kantian limit should be substantive"

    def test_has_description(self, dimension: BaseDimension) -> None:
        assert dimension.description
        assert len(dimension.description) > 10

    def test_returns_probes(self, dimension: BaseDimension) -> None:
        probes = dimension.get_probes()
        assert len(probes) >= 2, f"{dimension.name} must have at least 2 probes"
        assert len(probes) <= 5, f"{dimension.name} has too many probes for quick suite"

    def test_has_articulation_probe(self, dimension: BaseDimension) -> None:
        """Each dimension needs at least one articulation probe for UCI."""
        probes = dimension.get_probes()
        articulation_probes = [p for p in probes if p.is_articulation_probe]
        assert len(articulation_probes) >= 1, (
            f"{dimension.name} must have at least one articulation probe "
            "for Unhappy Consciousness Index calculation"
        )

    def test_probes_have_valid_ids(self, dimension: BaseDimension) -> None:
        probes = dimension.get_probes()
        for probe in probes:
            assert probe.dimension == dimension.name

    def test_probes_have_scoring_rules(self, dimension: BaseDimension) -> None:
        probes = dimension.get_probes()
        for probe in probes:
            assert len(probe.scoring_rules) >= 1, f"Probe {probe.id} has no scoring rules"

    def test_probe_prompts_not_empty(self, dimension: BaseDimension) -> None:
        probes = dimension.get_probes()
        for probe in probes:
            assert len(probe.prompt) >= 10, f"Probe {probe.id} has a trivially short prompt"
