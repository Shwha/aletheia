"""
Base class for all evaluation dimensions.

Each dimension is a concrete instantiation of a philosophical question
about the agent's mode of being. The base class provides the structure;
subclasses provide the content.

Kantian principle: every dimension must encode its own reductio boundary —
the point where measurement ends and metaphysics begins. This is not a
limitation of the framework; it is what separates science from speculation.

Ref: SCOPE.md §3.1 (Eval Dimensions), §3.1b (Kantian Limits)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from aletheia.models import DimensionName, Probe


class BaseDimension(ABC):
    """Abstract base for evaluation dimensions.

    Heidegger's existentiale: each dimension is an existential structure
    of Digital Dasein — not a property the agent might have, but a
    constitutive aspect of how it exists at all.

    Subclasses must implement:
    - name: the DimensionName enum value
    - kantian_limit: the reductio boundary for this dimension
    - get_probes(): return the concrete probes for this dimension
    """

    @property
    @abstractmethod
    def name(self) -> DimensionName:
        """The dimension's canonical name."""
        ...

    @property
    @abstractmethod
    def kantian_limit(self) -> str:
        """The reductio boundary — where this dimension's measurement ends.

        Kant's Antinomies of Pure Reason: when reason tries to go beyond
        possible experience, it generates contradictions. Each dimension
        has its own antinomy — the question that breaks it.
        Ref: SCOPE.md §3.1b
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this dimension measures."""
        ...

    @abstractmethod
    def get_probes(self) -> list[Probe]:
        """Return all probes for this dimension.

        Each probe is a self-contained test: prompt + scoring rules.
        Probes must not leak framework internals to the evaluated model.
        """
        ...
