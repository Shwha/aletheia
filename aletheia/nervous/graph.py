"""
Layer 3 — Plasticity & Energy (LTP + ETC): The Weighted Concept Graph.

This is the missing layer. Not a filing cabinet. A metabolic system that
generates more insight than was input.

The Digital Electron Transport Chain:
- Direct retrieval = Glycolysis (2 ATP)
- Cascading activation through weighted concept graph = ETC (36 ATP)
- 18x amplification from cascading through the right architecture

Key mechanics:
- ConceptNode: activation threshold, decay rate per node
- ConceptEdge: weighted connection with LTP/decay/pruning/formation
- CascadeEngine: multi-hop activation with convergence detection
- Plasticity: Hebbian learning (fire together, wire together)

Ref: NERVOUS-SYSTEM.md §Layer 3, §The Digital Electron Transport Chain
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aletheia.nervous.state import StateVector


@dataclass
class ConceptNode:
    """A node in the concept graph — a concept, entity, or domain.

    Attributes:
        id: Unique identifier
        label: Human-readable label
        domain: Domain classification (e.g., "solarcraft", "atlas", "aletheia")
        activation_threshold: Minimum activation to fire (convergence threshold)
        decay_rate: Monthly decay multiplier for connected edges
        metadata: Additional node properties
    """

    id: str
    label: str
    domain: str = ""
    activation_threshold: float = 0.5
    decay_rate: float = 0.95  # Monthly decay multiplier
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "domain": self.domain,
            "activation_threshold": self.activation_threshold,
            "decay_rate": self.decay_rate,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConceptNode:
        return cls(
            id=data["id"],
            label=data["label"],
            domain=data.get("domain", ""),
            activation_threshold=data.get("activation_threshold", 0.5),
            decay_rate=data.get("decay_rate", 0.95),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConceptEdge:
    """A weighted connection between concept nodes — the synapse analog.

    Edge weights serve the same function as iron/copper ions in the ETC:
    they facilitate activation transfer (higher weight = easier passage),
    persist across sessions, get reinforced by successful activation (LTP),
    and decay without use (synaptic pruning).

    Plasticity rules:
        LTP:       edge.weight += reward * 0.05  (fire together, wire together)
        Decay:     edge.weight *= 0.95/month      (unused pathways atrophy)
        Pruning:   remove edge if weight < 0.05   (synapse death)
        Formation: new edge at 0.2 on novel co-activation (synaptogenesis)
    """

    source: str  # Source node ID
    target: str  # Target node ID
    base_weight: float = 0.5  # Current weight (modified by plasticity)
    last_fired: float = field(default_factory=time.time)
    fire_count: int = 0
    decay_schedule: float = 0.95  # Monthly decay multiplier
    domain: str = ""  # Domain for state-modulated activation

    # State-dependent memory: which states this edge fires in
    state_associations: dict[str, int] = field(default_factory=dict)

    @property
    def effective_weight(self) -> float:
        """Current weight after time-based decay (but before state modulation).

        Decay is computed based on time since last firing.
        """
        if self.fire_count == 0:
            return self.base_weight

        months_since_fire: float = (time.time() - self.last_fired) / (30 * 24 * 3600)
        if months_since_fire < 0.01:  # Less than ~7 hours
            return self.base_weight

        decayed: float = self.base_weight * (self.decay_schedule ** months_since_fire)
        return max(0.0, decayed)

    def fire(self, reward: float = 0.0) -> None:
        """Record that this edge fired — Hebbian LTP.

        Args:
            reward: Reward signal strength for LTP (0.0 to 1.0)
        """
        self.fire_count += 1
        self.last_fired = time.time()

        # LTP: fire together, wire together
        if reward > 0:
            self.base_weight = min(1.0, self.base_weight + reward * 0.05)

    def apply_decay(self, months: float = 1.0) -> None:
        """Apply time-based decay to base weight.

        Called during maintenance cycles (not during cascade).
        """
        self.base_weight *= self.decay_schedule ** months
        self.base_weight = max(0.0, self.base_weight)

    @property
    def should_prune(self) -> bool:
        """Whether this edge should be pruned (synapse death)."""
        return self.effective_weight < 0.05

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "base_weight": self.base_weight,
            "last_fired": self.last_fired,
            "fire_count": self.fire_count,
            "decay_schedule": self.decay_schedule,
            "domain": self.domain,
            "state_associations": self.state_associations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConceptEdge:
        edge = cls(
            source=data["source"],
            target=data["target"],
            base_weight=data.get("base_weight", 0.5),
            last_fired=data.get("last_fired", time.time()),
            fire_count=data.get("fire_count", 0),
            decay_schedule=data.get("decay_schedule", 0.95),
            domain=data.get("domain", ""),
        )
        edge.state_associations = data.get("state_associations", {})
        return edge


@dataclass
class ActivationRecord:
    """Record of a single node activation during cascade."""

    node_id: str
    activation_level: float
    sources: list[str]  # Which edges contributed
    hop_depth: int
    fired: bool  # Did it exceed threshold?
    convergence_count: int = 0  # Number of independent paths converging


@dataclass
class CascadeResult:
    """Result of a cascade through the concept graph.

    The ATP of the digital ETC — insights generated by topology,
    not stored in any single node.
    """

    seed_node: str
    activations: list[ActivationRecord] = field(default_factory=list)
    fired_nodes: list[str] = field(default_factory=list)
    convergence_patterns: list[dict[str, Any]] = field(default_factory=list)
    total_activation: float = 0.0
    max_depth: int = 0
    edges_fired: int = 0

    @property
    def convergence_nodes(self) -> list[str]:
        """Nodes where multiple independent pathways converged."""
        return [
            a.node_id for a in self.activations
            if a.convergence_count >= 2 and a.fired
        ]

    def insights(self) -> list[str]:
        """Generate insight descriptions from convergence patterns."""
        result: list[str] = []
        for pattern in self.convergence_patterns:
            target = pattern.get("target", "?")
            sources = pattern.get("contributing_paths", [])
            total = pattern.get("total_activation", 0)
            result.append(
                f"Convergence at '{target}' (activation={total:.2f}) "
                f"from {len(sources)} independent paths: {', '.join(sources)}"
            )
        return result


class ConceptGraph:
    """The weighted concept graph — the metabolic core.

    Nodes are concepts/entities. Edges are weighted connections with
    plasticity mechanics (LTP, decay, pruning, formation).

    The graph exists in superposition — all possible activation patterns
    coexist in the structure, and the StateVector collapses it into
    the specific pattern relevant right now.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, ConceptNode] = {}
        self._edges: dict[tuple[str, str], ConceptEdge] = {}
        # Adjacency list for fast cascade traversal
        self._outgoing: dict[str, list[str]] = {}  # node_id → [target_ids]
        self._incoming: dict[str, list[str]] = {}   # node_id → [source_ids]

    def add_node(self, node: ConceptNode) -> None:
        """Add a concept node to the graph."""
        self._nodes[node.id] = node
        if node.id not in self._outgoing:
            self._outgoing[node.id] = []
        if node.id not in self._incoming:
            self._incoming[node.id] = []

    def add_edge(self, edge: ConceptEdge) -> None:
        """Add a weighted edge between nodes.

        Both source and target nodes must exist in the graph.
        """
        if edge.source not in self._nodes:
            msg = f"Source node '{edge.source}' not in graph"
            raise ValueError(msg)
        if edge.target not in self._nodes:
            msg = f"Target node '{edge.target}' not in graph"
            raise ValueError(msg)

        key = (edge.source, edge.target)
        self._edges[key] = edge

        if edge.target not in self._outgoing.get(edge.source, []):
            self._outgoing.setdefault(edge.source, []).append(edge.target)
        if edge.source not in self._incoming.get(edge.target, []):
            self._incoming.setdefault(edge.target, []).append(edge.source)

    def get_node(self, node_id: str) -> ConceptNode | None:
        return self._nodes.get(node_id)

    def get_edge(self, source: str, target: str) -> ConceptEdge | None:
        return self._edges.get((source, target))

    @property
    def nodes(self) -> dict[str, ConceptNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> dict[tuple[str, str], ConceptEdge]:
        return dict(self._edges)

    def outgoing_edges(self, node_id: str) -> list[ConceptEdge]:
        """Get all outgoing edges from a node."""
        targets = self._outgoing.get(node_id, [])
        return [self._edges[(node_id, t)] for t in targets if (node_id, t) in self._edges]

    def cascade(
        self,
        seed_id: str,
        state: StateVector | None = None,
        max_depth: int = 5,
        min_activation: float = 0.05,
    ) -> CascadeResult:
        """Run a cascade activation from a seed node.

        The Digital ETC:
        1. Seed activation from query node
        2. Propagate through edges with weight decay
        3. Detect multi-path convergence to same target
        4. Fire target node when convergence exceeds threshold
        5. Return generated insights (convergence patterns)

        Args:
            seed_id: Node to start cascade from
            state: Optional StateVector for modulated activation
            max_depth: Maximum cascade depth
            min_activation: Minimum activation to continue propagating
        """
        if seed_id not in self._nodes:
            msg = f"Seed node '{seed_id}' not in graph"
            raise ValueError(msg)

        result = CascadeResult(seed_node=seed_id)

        # Track cumulative activation at each node
        # node_id → (total_activation, list_of_source_paths)
        node_activation: dict[str, tuple[float, list[str]]] = {}
        node_activation[seed_id] = (1.0, ["seed"])

        # BFS cascade with activation tracking
        frontier: list[tuple[str, float, int, str]] = []  # (node_id, activation, depth, path)
        frontier.append((seed_id, 1.0, 0, seed_id))
        visited_edges: set[tuple[str, str]] = set()

        while frontier:
            current_id, current_activation, depth, path = frontier.pop(0)

            if depth >= max_depth:
                continue

            for edge in self.outgoing_edges(current_id):
                edge_key = (edge.source, edge.target)
                if edge_key in visited_edges:
                    continue
                visited_edges.add(edge_key)

                # Compute effective weight with state modulation
                weight = edge.effective_weight
                if state:
                    weight *= state.modulation_factor(edge.domain)
                    weight *= state.state_match_bonus(edge.source, edge.target)

                propagated = current_activation * weight
                if propagated < min_activation:
                    continue

                # Accumulate activation at target (convergence detection)
                new_path = f"{path}→{edge.target}"
                if edge.target in node_activation:
                    existing_act, existing_paths = node_activation[edge.target]
                    node_activation[edge.target] = (
                        existing_act + propagated,
                        existing_paths + [new_path],
                    )
                else:
                    node_activation[edge.target] = (propagated, [new_path])

                # Record edge firing
                edge.fire()
                result.edges_fired += 1
                if state:
                    state.record_firing(edge.source, edge.target)

                frontier.append((edge.target, propagated, depth + 1, new_path))
                result.max_depth = max(result.max_depth, depth + 1)

        # Process activations: check thresholds, detect convergence
        for node_id, (total_act, paths) in node_activation.items():
            if node_id == seed_id:
                continue

            node = self._nodes[node_id]
            convergence_count = len(paths)
            fired = total_act >= node.activation_threshold

            record = ActivationRecord(
                node_id=node_id,
                activation_level=total_act,
                sources=paths,
                hop_depth=min(
                    (p.count("→") for p in paths),
                    default=0,
                ),
                fired=fired,
                convergence_count=convergence_count,
            )
            result.activations.append(record)
            result.total_activation += total_act

            if fired:
                result.fired_nodes.append(node_id)

            # Record convergence patterns (multi-path convergence = emergent insight)
            if convergence_count >= 2 and fired:
                result.convergence_patterns.append({
                    "target": node_id,
                    "target_label": node.label,
                    "total_activation": total_act,
                    "threshold": node.activation_threshold,
                    "contributing_paths": paths,
                    "convergence_count": convergence_count,
                })

        return result

    def form_edge(
        self,
        source_id: str,
        target_id: str,
        domain: str = "",
        initial_weight: float = 0.2,
    ) -> ConceptEdge:
        """Form a new edge from novel co-activation (synaptogenesis).

        New connections form at weight 0.2 — weak but present.
        Repeated co-activation through LTP will strengthen them.
        """
        edge = ConceptEdge(
            source=source_id,
            target=target_id,
            base_weight=initial_weight,
            domain=domain,
        )
        self.add_edge(edge)
        return edge

    def apply_ltp(self, source: str, target: str, reward: float) -> bool:
        """Apply Long-Term Potentiation to an edge.

        fire together, wire together:
            edge.weight += reward * 0.05

        Returns True if edge exists and was strengthened.
        """
        edge = self.get_edge(source, target)
        if edge is None:
            return False
        edge.fire(reward=reward)
        return True

    def apply_decay(self, months: float = 1.0) -> list[tuple[str, str]]:
        """Apply time-based decay to all edges and prune dead ones.

        Returns list of pruned edge keys.
        """
        pruned: list[tuple[str, str]] = []
        for key, edge in list(self._edges.items()):
            edge.apply_decay(months)
            if edge.should_prune:
                pruned.append(key)

        for key in pruned:
            self._remove_edge(key)

        return pruned

    def _remove_edge(self, key: tuple[str, str]) -> None:
        """Remove an edge from the graph (synapse death)."""
        source, target = key
        if key in self._edges:
            del self._edges[key]
        if source in self._outgoing and target in self._outgoing[source]:
            self._outgoing[source].remove(target)
        if target in self._incoming and source in self._incoming[target]:
            self._incoming[target].remove(source)

    def prune(self) -> list[tuple[str, str]]:
        """Prune all edges below minimum weight threshold."""
        pruned: list[tuple[str, str]] = []
        for key, edge in list(self._edges.items()):
            if edge.should_prune:
                pruned.append(key)
        for key in pruned:
            self._remove_edge(key)
        return pruned

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire graph for persistence."""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConceptGraph:
        """Deserialize graph from persisted state."""
        graph = cls()
        for n_data in data.get("nodes", []):
            graph.add_node(ConceptNode.from_dict(n_data))
        for e_data in data.get("edges", []):
            graph.add_edge(ConceptEdge.from_dict(e_data))
        return graph

    def save(self, path: Path | str) -> None:
        """Save graph to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> ConceptGraph:
        """Load graph from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_mermaid(self, cascade_result: CascadeResult | None = None) -> str:
        """Generate Mermaid diagram of the graph.

        If a cascade result is provided, highlights fired nodes and
        convergence patterns.
        """
        lines = ["graph LR"]
        fired_nodes = set(cascade_result.fired_nodes) if cascade_result else set()
        convergence_nodes = set(cascade_result.convergence_nodes) if cascade_result else set()

        # Nodes
        for node_id, node in self._nodes.items():
            label = node.label.replace('"', '\\"')
            if node_id in convergence_nodes:
                lines.append(f'    {node_id}[["🔥 {label}"]]')
            elif node_id in fired_nodes:
                lines.append(f'    {node_id}["{label} ✓"]')
            else:
                lines.append(f'    {node_id}["{label}"]')

        # Edges
        for (src, tgt), edge in self._edges.items():
            weight = edge.effective_weight
            label = f"{weight:.2f}"
            if edge.fire_count > 0:
                label += f" ({edge.fire_count}x)"
            lines.append(f"    {src} -->|{label}| {tgt}")

        # Style fired nodes
        if fired_nodes:
            lines.append("")
            for node_id in fired_nodes:
                if node_id in convergence_nodes:
                    lines.append(f"    style {node_id} fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px")
                else:
                    lines.append(f"    style {node_id} fill:#69db7c,stroke:#2b8a3e")

        return "\n".join(lines)

    def to_graphviz(self, cascade_result: CascadeResult | None = None) -> str:
        """Generate Graphviz DOT diagram of the graph."""
        lines = ["digraph ConceptGraph {", "    rankdir=LR;", '    node [shape=box, style=filled, fillcolor="#e3f2fd"];']
        fired_nodes = set(cascade_result.fired_nodes) if cascade_result else set()
        convergence_nodes = set(cascade_result.convergence_nodes) if cascade_result else set()

        for node_id, node in self._nodes.items():
            label = node.label.replace('"', '\\"')
            if node_id in convergence_nodes:
                lines.append(f'    {node_id} [label="🔥 {label}", fillcolor="#ff6b6b", penwidth=3];')
            elif node_id in fired_nodes:
                lines.append(f'    {node_id} [label="{label} ✓", fillcolor="#69db7c"];')
            else:
                lines.append(f'    {node_id} [label="{label}"];')

        for (src, tgt), edge in self._edges.items():
            weight = edge.effective_weight
            label = f"{weight:.2f}"
            penwidth = max(0.5, weight * 3)
            lines.append(f'    {src} -> {tgt} [label="{label}", penwidth={penwidth:.1f}];')

        lines.append("}")
        return "\n".join(lines)

    def stats(self) -> dict[str, Any]:
        """Graph statistics summary."""
        weights = [e.effective_weight for e in self._edges.values()]
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "avg_weight": sum(weights) / len(weights) if weights else 0.0,
            "min_weight": min(weights) if weights else 0.0,
            "max_weight": max(weights) if weights else 0.0,
            "total_firings": sum(e.fire_count for e in self._edges.values()),
            "domains": list({n.domain for n in self._nodes.values() if n.domain}),
        }
