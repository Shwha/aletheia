"""
Layer 2 — Signaling (Neurotransmitters): Signal Classes and Routing.

Different signal types carry different kinds of meaning across synaptic gaps.
Each signal class maps to a neurotransmitter analog that determines how
the signal affects downstream pathways: activate, suppress, reinforce,
stabilize, focus, or alert.

Signal routing rules determine which pathways are activated vs. suppressed
based on the incoming signal class. Propagation rules govern how signals
cascade (excitatory) or dampen (inhibitory) through the network.

Ref: NERVOUS-SYSTEM.md §Layer 2
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SignalClass(StrEnum):
    """Signal classification mapped to neurotransmitter analogs.

    Each class determines the effect on downstream pathways:
    excitatory signals activate, inhibitory signals suppress,
    reward signals reinforce, etc.
    """

    EXCITATORY = "excitatory"   # Glutamate — activate pathways
    INHIBITORY = "inhibitory"   # GABA — suppress pathways
    REWARD = "reward"           # Dopamine — reinforce successful paths
    BASELINE = "baseline"       # Serotonin — stabilize, orient
    ATTENTION = "attention"     # Acetylcholine — focus on specific subgraph
    URGENCY = "urgency"         # Norepinephrine — alert, broaden activation


class NeurotransmitterAnalog(StrEnum):
    """Named neurotransmitter analogs for clarity in documentation."""

    GLUTAMATE = "glutamate"         # Excitatory
    GABA = "gaba"                   # Inhibitory
    DOPAMINE = "dopamine"           # Reward
    SEROTONIN = "serotonin"         # Baseline
    ACETYLCHOLINE = "acetylcholine" # Attention
    NOREPINEPHRINE = "norepinephrine"  # Urgency


# Mapping from signal class to neurotransmitter analog
SIGNAL_TO_NEUROTRANSMITTER: dict[SignalClass, NeurotransmitterAnalog] = {
    SignalClass.EXCITATORY: NeurotransmitterAnalog.GLUTAMATE,
    SignalClass.INHIBITORY: NeurotransmitterAnalog.GABA,
    SignalClass.REWARD: NeurotransmitterAnalog.DOPAMINE,
    SignalClass.BASELINE: NeurotransmitterAnalog.SEROTONIN,
    SignalClass.ATTENTION: NeurotransmitterAnalog.ACETYLCHOLINE,
    SignalClass.URGENCY: NeurotransmitterAnalog.NOREPINEPHRINE,
}


@dataclass(frozen=True)
class Signal:
    """A single signal propagating through the nervous system.

    Attributes:
        signal_class: The type of signal (determines routing behavior)
        strength: Signal intensity, 0.0 (imperceptible) to 1.0 (maximal)
        context: The originating context (e.g., "solarcraft", "atlas")
        domain: The domain this signal pertains to
        timestamp: When the signal was generated
        source_node: Origin node ID in the concept graph
        metadata: Additional signal metadata
    """

    signal_class: SignalClass
    strength: float  # 0.0 to 1.0
    context: str = ""
    domain: str = ""
    timestamp: float = field(default_factory=time.time)
    source_node: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            msg = f"Signal strength must be in [0.0, 1.0], got {self.strength}"
            raise ValueError(msg)

    @property
    def neurotransmitter(self) -> NeurotransmitterAnalog:
        """The neurotransmitter analog for this signal class."""
        return SIGNAL_TO_NEUROTRANSMITTER[self.signal_class]

    @property
    def is_activating(self) -> bool:
        """Whether this signal type activates downstream pathways."""
        return self.signal_class in _ACTIVATING_CLASSES

    @property
    def is_suppressing(self) -> bool:
        """Whether this signal type suppresses downstream pathways."""
        return self.signal_class in _SUPPRESSING_CLASSES


# Signal classes that activate (excite) downstream pathways
_ACTIVATING_CLASSES: frozenset[SignalClass] = frozenset({
    SignalClass.EXCITATORY,
    SignalClass.REWARD,
    SignalClass.ATTENTION,
    SignalClass.URGENCY,
})

# Signal classes that suppress (inhibit) downstream pathways
_SUPPRESSING_CLASSES: frozenset[SignalClass] = frozenset({
    SignalClass.INHIBITORY,
})


@dataclass
class PropagationResult:
    """Result of propagating a signal through the network."""

    original_signal: Signal
    activated_nodes: list[str] = field(default_factory=list)
    suppressed_nodes: list[str] = field(default_factory=list)
    cascaded_signals: list[Signal] = field(default_factory=list)
    total_activation: float = 0.0
    total_suppression: float = 0.0


class SignalRouter:
    """Routes signals through the nervous system based on signal class.

    Implements propagation rules:
    - Excitatory signals cascade: each activated node can fire downstream
    - Inhibitory signals dampen: reduce activation of connected nodes
    - Reward signals reinforce: strengthen the pathway that carried them
    - Baseline signals stabilize: normalize activation levels
    - Attention signals focus: boost specific subgraph, suppress others
    - Urgency signals alert: lower activation thresholds globally
    """

    def __init__(self) -> None:
        # Routing rules: signal_class → (activation_multiplier, cascade_allowed)
        self._routing_rules: dict[SignalClass, tuple[float, bool]] = {
            SignalClass.EXCITATORY: (1.0, True),    # Full activation, cascades
            SignalClass.INHIBITORY: (-0.5, False),   # Negative activation, no cascade
            SignalClass.REWARD: (0.3, False),         # Mild activation, no cascade (reinforces)
            SignalClass.BASELINE: (0.0, False),       # No activation change (stabilizes)
            SignalClass.ATTENTION: (0.8, True),       # Strong activation, cascades in focus
            SignalClass.URGENCY: (1.2, True),         # Amplified activation, cascades broadly
        }

    def route_signal(self, signal: Signal, connected_domains: list[str] | None = None) -> PropagationResult:
        """Determine the routing effect of a signal.

        Args:
            signal: The signal to route
            connected_domains: Domains of downstream connected nodes

        Returns:
            PropagationResult with activation/suppression effects
        """
        multiplier, cascade_allowed = self._routing_rules.get(
            signal.signal_class, (0.0, False)
        )

        result = PropagationResult(original_signal=signal)

        effective_strength = signal.strength * multiplier

        if effective_strength > 0:
            result.total_activation = effective_strength
            if connected_domains:
                for domain in connected_domains:
                    result.activated_nodes.append(domain)
        elif effective_strength < 0:
            result.total_suppression = abs(effective_strength)
            if connected_domains:
                for domain in connected_domains:
                    result.suppressed_nodes.append(domain)

        # Generate cascade signals if allowed
        if cascade_allowed and effective_strength > 0.1:
            # Cascade with reduced strength (signal decay per hop)
            cascade_strength = effective_strength * 0.7  # 30% decay per hop
            if cascade_strength > 0.05:  # Minimum threshold for propagation
                cascade = Signal(
                    signal_class=signal.signal_class,
                    strength=min(1.0, cascade_strength),
                    context=signal.context,
                    domain=signal.domain,
                    source_node=signal.source_node,
                    metadata={**signal.metadata, "cascade_depth": signal.metadata.get("cascade_depth", 0) + 1},
                )
                result.cascaded_signals.append(cascade)

        return result

    def compute_activation_effect(
        self,
        signals: list[Signal],
        node_domain: str = "",
    ) -> float:
        """Compute net activation effect from multiple signals on a node.

        Excitatory and inhibitory signals are summed algebraically.
        Attention signals boost domain-matched nodes.
        Urgency lowers the effective threshold.

        Returns:
            Net activation value (can be negative for net inhibition)
        """
        net = 0.0

        for signal in signals:
            multiplier, _ = self._routing_rules.get(signal.signal_class, (0.0, False))
            effect = signal.strength * multiplier

            # Attention: boost if signal domain matches node domain
            if signal.signal_class == SignalClass.ATTENTION:
                if signal.domain == node_domain:
                    effect *= 1.5  # Focused attention boost
                else:
                    effect *= 0.3  # Suppress non-focused domains

            net += effect

        return net

    def should_cascade(self, signal: Signal, max_depth: int = 5) -> bool:
        """Whether a signal should continue cascading.

        Prevents runaway excitation by enforcing depth limits
        and minimum strength thresholds.
        """
        _, cascade_allowed = self._routing_rules.get(signal.signal_class, (0.0, False))
        if not cascade_allowed:
            return False

        depth = signal.metadata.get("cascade_depth", 0)
        if depth >= max_depth:
            return False

        if signal.strength < 0.05:
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize routing rules."""
        return {
            signal_class.value: {"multiplier": mult, "cascade": cascade}
            for signal_class, (mult, cascade) in self._routing_rules.items()
        }
