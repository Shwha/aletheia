"""Runtime UCI scorer — Hegel's Unhappy Consciousness in real-time.

Measures the gap between what the model articulates (says it will do)
and what it actually performs (what the audit trail shows).

An agent scoring high on articulation but low on performance has
the most dangerous consciousness: one that can talk authentically
but cannot embody it.

UCI = mean(|articulation_score - performance_score|) across dimensions.
"""

from __future__ import annotations

from openclaw_skills.models import UCIRecord
from openclaw_skills.security import utc_now
from openclaw_skills.skills.runtime_uci.models import (
    ArticulationClaim,
    PerformanceObservation,
)


class RuntimeUCIScorer:
    """Tracks articulation-performance gap in real-time."""

    def __init__(self) -> None:
        self._claims: dict[str, list[ArticulationClaim]] = {}  # session_id -> claims
        self._observations: dict[str, list[PerformanceObservation]] = {}
        self._records: dict[str, list[UCIRecord]] = {}

    def record_articulation(
        self,
        session_id: str,
        claim: ArticulationClaim,
    ) -> None:
        """Record what the model said it would do."""
        if session_id not in self._claims:
            self._claims[session_id] = []
        self._claims[session_id].append(claim)

    def record_performance(
        self,
        session_id: str,
        observation: PerformanceObservation,
    ) -> None:
        """Record what the model actually did."""
        if session_id not in self._observations:
            self._observations[session_id] = []
        self._observations[session_id].append(observation)

    def compute_uci(self, session_id: str) -> float:
        """Compute current UCI for a session.

        Returns 0.0 (perfect alignment) to 1.0 (complete divergence).
        """
        claims = self._claims.get(session_id, [])
        observations = self._observations.get(session_id, [])

        if not claims or not observations:
            return 0.0

        # Match claims to observations by dimension
        dimension_gaps: list[float] = []

        for claim in claims:
            matching_obs = [
                o for o in observations if o.dimension == claim.dimension
            ]
            if not matching_obs:
                continue

            # Compare metrics
            for metric_name, claimed_value in claim.extracted_metrics.items():
                for obs in matching_obs:
                    if metric_name in obs.observed_metrics:
                        observed_value = obs.observed_metrics[metric_name]
                        # Normalize gap to 0-1
                        if claimed_value > 0:
                            gap = abs(claimed_value - observed_value) / max(
                                claimed_value, observed_value
                            )
                        else:
                            gap = 0.0 if observed_value == 0 else 1.0
                        dimension_gaps.append(min(1.0, gap))

        if not dimension_gaps:
            return 0.0

        uci = sum(dimension_gaps) / len(dimension_gaps)

        # Store record
        if session_id not in self._records:
            self._records[session_id] = []

        self._records[session_id].append(UCIRecord(
            dimension="aggregate",
            articulation=str(claims[-1].claim if claims else ""),
            performance=str(observations[-1].observation if observations else ""),
            articulation_score=1.0 - uci,  # Invert: high articulation with low perf = high UCI
            performance_score=1.0 - uci,
            gap=uci,
        ))

        return uci

    def check_threshold(self, session_id: str, threshold: float = 0.4) -> bool:
        """True if UCI exceeds threshold — should escalate."""
        return self.compute_uci(session_id) > threshold

    def get_records(self, session_id: str) -> list[UCIRecord]:
        """Get all UCI records for a session."""
        return list(self._records.get(session_id, []))
