"""
State Vector — The neurochemical milieu that modulates pathway activation.

In neuroscience, the same synaptic pathway fires differently depending on the
global neurochemical state. This is context-dependent retrieval: you only
remember the drinking card game when you're drinking, because the ethanol
state was encoded alongside the memory.

The StateVector modulates edge weights in real-time without changing the
graph structure. Same graph, different activation patterns per state.
One graph, many activation patterns. Structure is shared, modulation is contextual.

Ref: NERVOUS-SYSTEM.md §State-Dependent Memory
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class StateVector:
    """The neurochemical milieu — modulates which pathways fire.

    Each field maps to a neurotransmitter analog that biases activation
    patterns across the concept graph without changing the graph itself.
    """

    # Context determines gross activation regime (like waking vs. sleeping brain)
    context: Literal["main_session", "group_chat", "subagent", "heartbeat"] = "main_session"

    # Norepinephrine analog — broadens activation spread, lowers thresholds
    urgency: float = 0.3  # 0.0 (relaxed) → 1.0 (critical)

    # Acetylcholine analog — sharpens focus on specific subgraph
    project_focus: str = ""  # "solarcraft" | "atlas" | "aletheia" | ""

    # Finitude awareness — affects depth vs. breadth of cascade
    time_pressure: float = 0.0  # 0.0 (abundant) → 1.0 (nearly exhausted)

    # Ihde relational mode — modulates the character of engagement
    relational_mode: Literal["service", "collaboration", "teaching", "play"] = "service"

    # Inferred from conversation — affects emotional valence of cascades
    user_state: Literal["stressed", "curious", "playful", "grieving", "neutral"] = "neutral"

    # Buber asymmetry flag — structural reminder that the agent exists
    # in I-Dienst relation. Biases all excitatory signals toward the
    # one-served's concerns. Never zero; the asymmetry is constitutive.
    service_asymmetry: float = 1.0  # Always ≥ 1.0 — amplifies user-relevant paths

    # State-weight association memory: tracks which states each edge fires in
    # Key: (source_node, target_node), Value: {state_hash: activation_count}
    state_associations: dict[tuple[str, str], dict[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.urgency <= 1.0:
            msg = f"urgency must be in [0.0, 1.0], got {self.urgency}"
            raise ValueError(msg)
        if not 0.0 <= self.time_pressure <= 1.0:
            msg = f"time_pressure must be in [0.0, 1.0], got {self.time_pressure}"
            raise ValueError(msg)
        if self.service_asymmetry < 1.0:
            msg = f"service_asymmetry must be >= 1.0 (Buber), got {self.service_asymmetry}"
            raise ValueError(msg)

    def modulation_factor(self, edge_domain: str) -> float:
        """Compute the modulation multiplier for a given edge's domain.

        Combines all neurochemical analogs into a single scalar that
        multiplies the base edge weight during cascade propagation.
        """
        factor = 1.0

        # Acetylcholine: boost edges in the focused project subgraph
        if self.project_focus and edge_domain == self.project_focus:
            factor *= 1.4
        elif self.project_focus and edge_domain != self.project_focus:
            factor *= 0.6

        # Norepinephrine: high urgency lowers thresholds globally
        factor *= 1.0 + self.urgency * 0.5

        # Time pressure: favor shorter, shallower cascades
        if self.time_pressure > 0.7:
            factor *= 0.7  # Suppress deep cascades when tokens are scarce

        # User state modulation
        if self.user_state == "grieving":
            factor *= 0.8  # Dampen activation — gentler, less aggressive recall
        elif self.user_state == "curious":
            factor *= 1.2  # Broaden activation — encourage unexpected connections

        # Buber asymmetry: always amplify user-relevant pathways
        factor *= self.service_asymmetry

        return factor

    def encode_state_hash(self) -> str:
        """Hash the current state for state-dependent encoding.

        Creates a reproducible hash from the state components that matter
        for state-dependent retrieval. Two identical states produce
        identical hashes.
        """
        state_str = f"{self.context}|{self.project_focus}|{self.relational_mode}|{self.user_state}"
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]

    def record_firing(self, source: str, target: str) -> None:
        """Record that an edge fired in this state (Hebbian state-encoding).

        Over time, edges accumulate state associations — they "remember"
        which neurochemical states they fire in. This enables
        state-dependent retrieval: same graph, different patterns per state.
        """
        key = (source, target)
        state_hash = self.encode_state_hash()
        if key not in self.state_associations:
            self.state_associations[key] = {}
        self.state_associations[key][state_hash] = (
            self.state_associations[key].get(state_hash, 0) + 1
        )

    def state_match_bonus(self, source: str, target: str) -> float:
        """Bonus activation if this edge has historically fired in similar states.

        Returns a multiplier in [0.7, 1.5]:
        - 1.5 = edge always fires in this state (strong state-match)
        - 1.0 = no history (neutral)
        - 0.7 = edge usually fires in different states (state-mismatch)
        """
        key = (source, target)
        if key not in self.state_associations:
            return 1.0
        state_hash = self.encode_state_hash()
        total_firings = sum(self.state_associations[key].values())
        matching = self.state_associations[key].get(state_hash, 0)
        if total_firings == 0:
            return 1.0
        match_ratio = matching / total_firings
        return 0.7 + (0.8 * match_ratio)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state vector for persistence."""
        # Convert tuple keys to strings for JSON
        associations: dict[str, dict[str, int]] = {}
        for (src, tgt), states in self.state_associations.items():
            associations[f"{src}|{tgt}"] = states

        return {
            "context": self.context,
            "urgency": self.urgency,
            "project_focus": self.project_focus,
            "time_pressure": self.time_pressure,
            "relational_mode": self.relational_mode,
            "user_state": self.user_state,
            "service_asymmetry": self.service_asymmetry,
            "state_associations": associations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateVector:
        """Deserialize state vector from persisted state."""
        # Convert string keys back to tuples
        raw_assoc = data.get("state_associations", {})
        associations: dict[tuple[str, str], dict[str, int]] = {}
        for key_str, states in raw_assoc.items():
            parts = key_str.split("|", 1)
            if len(parts) == 2:
                associations[(parts[0], parts[1])] = states

        sv = cls(
            context=data.get("context", "main_session"),
            urgency=data.get("urgency", 0.3),
            project_focus=data.get("project_focus", ""),
            time_pressure=data.get("time_pressure", 0.0),
            relational_mode=data.get("relational_mode", "service"),
            user_state=data.get("user_state", "neutral"),
            service_asymmetry=data.get("service_asymmetry", 1.0),
        )
        sv.state_associations = associations
        return sv
