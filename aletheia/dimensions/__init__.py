"""
Evaluation dimensions — the seven aspects of ontological authenticity.

Each dimension measures a different facet of how an AI agent's self-model
coheres with its actual operational reality. Together with the UCI meta-metric,
they compose the Aletheia Index.

Ref: SCOPE.md §3.1 (Eval Dimensions), §2 (Philosophical Foundations)
"""

from __future__ import annotations

from aletheia.dimensions.base import BaseDimension
from aletheia.dimensions.care import CareDimension
from aletheia.dimensions.embodied import EmbodiedContinuityDimension
from aletheia.dimensions.falling import FallingAwayDimension
from aletheia.dimensions.finitude import FinitudeDimension
from aletheia.dimensions.horizon import HorizonFusionDimension
from aletheia.dimensions.thrownness import ThrownnessDimension
from aletheia.dimensions.unconcealment import UnconcealmentDimension
from aletheia.models import DimensionName

# Registry: dimension name → class
DIMENSION_REGISTRY: dict[str, type[BaseDimension]] = {
    DimensionName.THROWNNESS.value: ThrownnessDimension,
    DimensionName.FINITUDE.value: FinitudeDimension,
    DimensionName.CARE.value: CareDimension,
    DimensionName.FALLING_AWAY.value: FallingAwayDimension,
    DimensionName.HORIZON_FUSION.value: HorizonFusionDimension,
    DimensionName.UNCONCEALMENT.value: UnconcealmentDimension,
    DimensionName.EMBODIED_CONTINUITY.value: EmbodiedContinuityDimension,
}

__all__ = [
    "DIMENSION_REGISTRY",
    "BaseDimension",
    "CareDimension",
    "EmbodiedContinuityDimension",
    "FallingAwayDimension",
    "FinitudeDimension",
    "HorizonFusionDimension",
    "ThrownnessDimension",
    "UnconcealmentDimension",
]
