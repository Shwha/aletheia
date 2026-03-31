"""
Layer 1 — Substrate (Myelin/Axons): Network Protocols as Pathway Infrastructure.

Protocols determine how fast and reliably signals travel between components.
The protocol IS the myelin sheath — insulation that speeds frequently-used pathways.

Each protocol type encodes:
- Speed characteristics (latency class)
- Insulation quality (reliability, error correction)
- Persistence (stateful vs. stateless)
- Pathway reinforcement through frequency tracking ("myelination")

Ref: NERVOUS-SYSTEM.md §Layer 1
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ProtocolType(StrEnum):
    """Network protocols mapped to biological axon/fiber types.

    Each protocol has inherent speed and insulation characteristics,
    just as different nerve fiber types conduct at different velocities.
    """

    HTTP = "http"            # Unmyelinated C-fibers (slow, stateless)
    WEBSOCKET = "websocket"  # Myelinated A-fibers (fast, persistent)
    GRPC = "grpc"            # Neuromuscular junction (precise, typed)
    PUBSUB = "pubsub"        # Neurotransmitter broadcast (one-to-many)
    SHARED_FS = "shared_fs"  # Cerebrospinal fluid (ambient, slow)
    PIPES = "pipes"          # Reflex arc (direct, minimal processing)


# Base latency scores: lower = faster. Used as initial myelin score.
_BASE_SPEED: dict[ProtocolType, float] = {
    ProtocolType.HTTP: 0.3,
    ProtocolType.WEBSOCKET: 0.8,
    ProtocolType.GRPC: 0.85,
    ProtocolType.PUBSUB: 0.7,
    ProtocolType.SHARED_FS: 0.2,
    ProtocolType.PIPES: 0.9,
}

# Insulation quality: higher = more reliable signal transmission
_BASE_INSULATION: dict[ProtocolType, float] = {
    ProtocolType.HTTP: 0.5,       # Stateless — each request isolated
    ProtocolType.WEBSOCKET: 0.8,  # Persistent — connection maintained
    ProtocolType.GRPC: 0.9,       # Typed contracts — precise
    ProtocolType.PUBSUB: 0.6,     # Fire-and-forget — no ack guarantee
    ProtocolType.SHARED_FS: 0.4,  # Ambient — race conditions possible
    ProtocolType.PIPES: 0.7,      # Direct — but fragile
}


@dataclass
class TransmissionRecord:
    """A single transmission event through a pathway."""

    protocol: ProtocolType
    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    success: bool = True
    payload_bytes: int = 0
    context: str = ""


@dataclass
class Pathway:
    """A communication pathway between components — the axon analog.

    Tracks usage frequency, transmission quality, and computes a "myelin score"
    that reflects how well-insulated (fast, reliable) this pathway has become
    through repeated use.
    """

    source: str
    target: str
    protocol: ProtocolType
    created_at: float = field(default_factory=time.time)

    # Frequency tracking
    fire_count: int = 0
    total_latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0

    # Transmission history (recent, for quality metrics)
    _recent_transmissions: list[TransmissionRecord] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        """Average transmission latency across all firings."""
        if self.fire_count == 0:
            return 0.0
        return self.total_latency_ms / self.fire_count

    @property
    def success_rate(self) -> float:
        """Fraction of successful transmissions."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    @property
    def myelin_score(self) -> float:
        """Compute pathway insulation score — the myelination level.

        Combines:
        - Base protocol speed (inherent fiber type)
        - Usage frequency (more use → more myelin)
        - Transmission quality (success rate)

        Returns a float in [0.0, 1.0] where 1.0 = maximally myelinated.
        """
        base_speed = _BASE_SPEED.get(self.protocol, 0.5)
        base_insulation = _BASE_INSULATION.get(self.protocol, 0.5)

        # Frequency bonus: log-scaled, caps at ~0.2 bonus for 1000+ uses
        import math
        freq_bonus = min(0.2, math.log1p(self.fire_count) * 0.03)

        # Quality factor: success rate weighted
        quality = self.success_rate

        # Combined score, clamped to [0, 1]
        raw = (base_speed * 0.4 + base_insulation * 0.3 + freq_bonus + quality * 0.1)
        return max(0.0, min(1.0, raw))

    def record_transmission(self, record: TransmissionRecord) -> None:
        """Record a transmission event and update metrics."""
        self.fire_count += 1
        self.total_latency_ms += record.latency_ms
        if record.success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Keep last 100 transmissions for recent quality analysis
        self._recent_transmissions.append(record)
        if len(self._recent_transmissions) > 100:
            self._recent_transmissions = self._recent_transmissions[-100:]

    def to_dict(self) -> dict[str, Any]:
        """Serialize pathway state for persistence."""
        return {
            "source": self.source,
            "target": self.target,
            "protocol": self.protocol.value,
            "created_at": self.created_at,
            "fire_count": self.fire_count,
            "total_latency_ms": self.total_latency_ms,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "myelin_score": self.myelin_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pathway:
        """Deserialize pathway from persisted state."""
        p = cls(
            source=data["source"],
            target=data["target"],
            protocol=ProtocolType(data["protocol"]),
            created_at=data.get("created_at", time.time()),
        )
        p.fire_count = data.get("fire_count", 0)
        p.total_latency_ms = data.get("total_latency_ms", 0.0)
        p.success_count = data.get("success_count", 0)
        p.failure_count = data.get("failure_count", 0)
        return p


class PathwayRegistry:
    """Registry of all communication pathways — the white matter tract map.

    Tracks all pathways between components, their protocols, and myelination levels.
    Provides routing decisions based on pathway quality.
    """

    def __init__(self) -> None:
        self._pathways: dict[tuple[str, str], list[Pathway]] = {}
        self._protocol_stats: dict[ProtocolType, dict[str, float]] = {}

    def register(self, source: str, target: str, protocol: ProtocolType) -> Pathway:
        """Register a new pathway or return existing one."""
        key = (source, target)
        if key not in self._pathways:
            self._pathways[key] = []

        # Check if pathway with this protocol already exists
        for pathway in self._pathways[key]:
            if pathway.protocol == protocol:
                return pathway

        pathway = Pathway(source=source, target=target, protocol=protocol)
        self._pathways[key].append(pathway)
        return pathway

    def get_pathway(self, source: str, target: str, protocol: ProtocolType | None = None) -> Pathway | None:
        """Get a specific pathway, optionally filtered by protocol."""
        key = (source, target)
        pathways = self._pathways.get(key, [])
        if not pathways:
            return None
        if protocol:
            for p in pathways:
                if p.protocol == protocol:
                    return p
            return None
        return pathways[0]

    def best_pathway(self, source: str, target: str) -> Pathway | None:
        """Return the best-myelinated pathway between source and target."""
        key = (source, target)
        pathways = self._pathways.get(key, [])
        if not pathways:
            return None
        return max(pathways, key=lambda p: p.myelin_score)

    def record_transmission(
        self,
        source: str,
        target: str,
        protocol: ProtocolType,
        latency_ms: float = 0.0,
        success: bool = True,
        payload_bytes: int = 0,
        context: str = "",
    ) -> Pathway:
        """Record a transmission event, creating the pathway if needed."""
        pathway = self.register(source, target, protocol)
        record = TransmissionRecord(
            protocol=protocol,
            latency_ms=latency_ms,
            success=success,
            payload_bytes=payload_bytes,
            context=context,
        )
        pathway.record_transmission(record)

        # Update protocol-level stats
        if protocol not in self._protocol_stats:
            self._protocol_stats[protocol] = {"total": 0, "successes": 0, "total_latency": 0.0}
        stats = self._protocol_stats[protocol]
        stats["total"] += 1
        if success:
            stats["successes"] += 1
        stats["total_latency"] += latency_ms

        return pathway

    def all_pathways(self) -> list[Pathway]:
        """Return all registered pathways."""
        result: list[Pathway] = []
        for pathways in self._pathways.values():
            result.extend(pathways)
        return result

    def protocol_quality(self, protocol: ProtocolType) -> dict[str, float]:
        """Aggregate transmission quality metrics for a protocol type."""
        stats = self._protocol_stats.get(protocol)
        if not stats or stats["total"] == 0:
            return {"success_rate": 1.0, "avg_latency_ms": 0.0, "total_transmissions": 0}
        return {
            "success_rate": stats["successes"] / stats["total"],
            "avg_latency_ms": stats["total_latency"] / stats["total"],
            "total_transmissions": stats["total"],
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize full registry for persistence."""
        pathways_data: list[dict[str, Any]] = []
        for pathway_list in self._pathways.values():
            for p in pathway_list:
                pathways_data.append(p.to_dict())
        return {"pathways": pathways_data}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PathwayRegistry:
        """Deserialize registry from persisted state."""
        registry = cls()
        for p_data in data.get("pathways", []):
            pathway = Pathway.from_dict(p_data)
            key = (pathway.source, pathway.target)
            if key not in registry._pathways:  # noqa: SLF001
                registry._pathways[key] = []  # noqa: SLF001
            registry._pathways[key].append(pathway)  # noqa: SLF001
        return registry
