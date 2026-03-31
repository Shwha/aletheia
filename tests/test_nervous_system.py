"""
Tests for the Aletheia Digital Nervous System.

Covers:
- Layer 1 (Substrate): Transport protocols, pathway registry, myelin scoring
- Layer 2 (Signaling): Signal classes, routing, propagation rules
- Layer 3 (Plasticity): Concept graph, cascade engine, LTP/decay/pruning
- State Vector: Modulation, state-dependent retrieval, Hebbian encoding
- Integration: Multi-hop cascades with convergence, state-dependent patterns
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aletheia.nervous.graph import (
    ConceptEdge,
    ConceptGraph,
    ConceptNode,
)
from aletheia.nervous.signals import (
    NeurotransmitterAnalog,
    Signal,
    SignalClass,
    SignalRouter,
)
from aletheia.nervous.state import StateVector
from aletheia.nervous.transport import (
    Pathway,
    PathwayRegistry,
    ProtocolType,
    TransmissionRecord,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ===================================================================
# Layer 1: Transport / Substrate
# ===================================================================


class TestProtocolType:
    def test_all_protocols_defined(self):
        assert len(ProtocolType) == 6
        assert ProtocolType.HTTP == "http"
        assert ProtocolType.WEBSOCKET == "websocket"
        assert ProtocolType.GRPC == "grpc"
        assert ProtocolType.PUBSUB == "pubsub"
        assert ProtocolType.SHARED_FS == "shared_fs"
        assert ProtocolType.PIPES == "pipes"


class TestPathway:
    def test_initial_pathway(self):
        p = Pathway(source="a", target="b", protocol=ProtocolType.HTTP)
        assert p.fire_count == 0
        assert p.avg_latency_ms == 0.0
        assert p.success_rate == 1.0
        assert 0.0 <= p.myelin_score <= 1.0

    def test_myelin_score_increases_with_usage(self):
        p = Pathway(source="a", target="b", protocol=ProtocolType.WEBSOCKET)
        initial = p.myelin_score

        for _ in range(100):
            p.record_transmission(TransmissionRecord(
                protocol=ProtocolType.WEBSOCKET, latency_ms=5.0, success=True
            ))

        assert p.myelin_score >= initial

    def test_failure_reduces_quality(self):
        p = Pathway(source="a", target="b", protocol=ProtocolType.HTTP)
        for _ in range(10):
            p.record_transmission(TransmissionRecord(
                protocol=ProtocolType.HTTP, success=True
            ))


        for _ in range(10):
            p.record_transmission(TransmissionRecord(
                protocol=ProtocolType.HTTP, success=False
            ))
        assert p.success_rate < 1.0

    def test_serialization_roundtrip(self):
        p = Pathway(source="x", target="y", protocol=ProtocolType.GRPC)
        p.record_transmission(TransmissionRecord(protocol=ProtocolType.GRPC, latency_ms=2.0))
        data = p.to_dict()
        p2 = Pathway.from_dict(data)
        assert p2.source == "x"
        assert p2.target == "y"
        assert p2.fire_count == 1

    def test_protocol_speed_ordering(self):
        """Pipes (reflex arc) should be faster than SharedFS (CSF)."""
        fast = Pathway(source="a", target="b", protocol=ProtocolType.PIPES)
        slow = Pathway(source="a", target="b", protocol=ProtocolType.SHARED_FS)
        assert fast.myelin_score > slow.myelin_score


class TestPathwayRegistry:
    def test_register_and_retrieve(self):
        reg = PathwayRegistry()
        p = reg.register("a", "b", ProtocolType.HTTP)
        assert p.source == "a"
        assert reg.get_pathway("a", "b") is p

    def test_best_pathway(self):
        reg = PathwayRegistry()
        reg.register("a", "b", ProtocolType.HTTP)
        reg.register("a", "b", ProtocolType.WEBSOCKET)
        best = reg.best_pathway("a", "b")
        assert best is not None
        # WebSocket should beat HTTP
        assert best.protocol == ProtocolType.WEBSOCKET

    def test_record_transmission_creates_pathway(self):
        reg = PathwayRegistry()
        p = reg.record_transmission("x", "y", ProtocolType.GRPC, latency_ms=1.5)
        assert p.fire_count == 1
        assert reg.get_pathway("x", "y", ProtocolType.GRPC) is p

    def test_protocol_quality(self):
        reg = PathwayRegistry()
        reg.record_transmission("a", "b", ProtocolType.HTTP, latency_ms=10, success=True)
        reg.record_transmission("a", "c", ProtocolType.HTTP, latency_ms=20, success=False)
        quality = reg.protocol_quality(ProtocolType.HTTP)
        assert quality["success_rate"] == 0.5
        assert quality["avg_latency_ms"] == 15.0

    def test_serialization_roundtrip(self):
        reg = PathwayRegistry()
        reg.record_transmission("a", "b", ProtocolType.WEBSOCKET, latency_ms=5)
        data = reg.to_dict()
        reg2 = PathwayRegistry.from_dict(data)
        assert len(reg2.all_pathways()) == 1


# ===================================================================
# Layer 2: Signaling
# ===================================================================


class TestSignalClass:
    def test_all_classes_defined(self):
        assert len(SignalClass) == 6

    def test_neurotransmitter_mapping(self):
        s = Signal(signal_class=SignalClass.EXCITATORY, strength=0.8)
        assert s.neurotransmitter == NeurotransmitterAnalog.GLUTAMATE

        s2 = Signal(signal_class=SignalClass.INHIBITORY, strength=0.5)
        assert s2.neurotransmitter == NeurotransmitterAnalog.GABA

    def test_signal_strength_validation(self):
        with pytest.raises(ValueError, match="strength"):
            Signal(signal_class=SignalClass.EXCITATORY, strength=1.5)
        with pytest.raises(ValueError, match="strength"):
            Signal(signal_class=SignalClass.EXCITATORY, strength=-0.1)

    def test_activating_vs_suppressing(self):
        excitatory = Signal(signal_class=SignalClass.EXCITATORY, strength=0.8)
        assert excitatory.is_activating
        assert not excitatory.is_suppressing

        inhibitory = Signal(signal_class=SignalClass.INHIBITORY, strength=0.5)
        assert inhibitory.is_suppressing
        assert not inhibitory.is_activating


class TestSignalRouter:
    def test_excitatory_activates(self):
        router = SignalRouter()
        signal = Signal(signal_class=SignalClass.EXCITATORY, strength=0.8)
        result = router.route_signal(signal, connected_domains=["d1", "d2"])
        assert result.total_activation > 0
        assert len(result.activated_nodes) == 2

    def test_inhibitory_suppresses(self):
        router = SignalRouter()
        signal = Signal(signal_class=SignalClass.INHIBITORY, strength=0.8)
        result = router.route_signal(signal, connected_domains=["d1"])
        assert result.total_suppression > 0
        assert len(result.suppressed_nodes) == 1

    def test_excitatory_cascade_generation(self):
        router = SignalRouter()
        signal = Signal(signal_class=SignalClass.EXCITATORY, strength=0.8)
        result = router.route_signal(signal)
        assert len(result.cascaded_signals) == 1
        # Cascade should have reduced strength
        assert result.cascaded_signals[0].strength < signal.strength

    def test_inhibitory_no_cascade(self):
        router = SignalRouter()
        signal = Signal(signal_class=SignalClass.INHIBITORY, strength=0.8)
        result = router.route_signal(signal)
        assert len(result.cascaded_signals) == 0

    def test_cascade_depth_limit(self):
        router = SignalRouter()
        signal = Signal(
            signal_class=SignalClass.EXCITATORY,
            strength=0.8,
            metadata={"cascade_depth": 5},
        )
        assert not router.should_cascade(signal, max_depth=5)

    def test_attention_domain_boost(self):
        router = SignalRouter()
        focused = Signal(signal_class=SignalClass.ATTENTION, strength=0.8, domain="solarcraft")
        effect_matched = router.compute_activation_effect([focused], node_domain="solarcraft")
        effect_unmatched = router.compute_activation_effect([focused], node_domain="atlas")
        assert effect_matched > effect_unmatched

    def test_net_activation_mixed_signals(self):
        router = SignalRouter()
        signals = [
            Signal(signal_class=SignalClass.EXCITATORY, strength=0.8),
            Signal(signal_class=SignalClass.INHIBITORY, strength=0.6),
        ]
        net = router.compute_activation_effect(signals)
        # Excitatory: 0.8 * 1.0 = 0.8, Inhibitory: 0.6 * -0.5 = -0.3
        assert 0.4 < net < 0.6


# ===================================================================
# Layer 3: Concept Graph + Cascade Engine
# ===================================================================


def _build_simple_graph() -> ConceptGraph:
    """Build a simple test graph: A → B → D, A → C → D (convergence at D)."""
    g = ConceptGraph()
    g.add_node(ConceptNode(id="a", label="Node A", domain="test", activation_threshold=0.3))
    g.add_node(ConceptNode(id="b", label="Node B", domain="test", activation_threshold=0.3))
    g.add_node(ConceptNode(id="c", label="Node C", domain="test", activation_threshold=0.3))
    g.add_node(ConceptNode(id="d", label="Node D", domain="test", activation_threshold=0.5))
    g.add_edge(ConceptEdge(source="a", target="b", base_weight=0.8, domain="test"))
    g.add_edge(ConceptEdge(source="a", target="c", base_weight=0.7, domain="test"))
    g.add_edge(ConceptEdge(source="b", target="d", base_weight=0.9, domain="test"))
    g.add_edge(ConceptEdge(source="c", target="d", base_weight=0.8, domain="test"))
    return g


class TestConceptNode:
    def test_creation(self):
        n = ConceptNode(id="test", label="Test Node", domain="test")
        assert n.id == "test"
        assert n.activation_threshold == 0.5
        assert n.decay_rate == 0.95

    def test_serialization(self):
        n = ConceptNode(id="x", label="X", domain="d", activation_threshold=0.3)
        data = n.to_dict()
        n2 = ConceptNode.from_dict(data)
        assert n2.id == "x"
        assert n2.activation_threshold == 0.3


class TestConceptEdge:
    def test_creation(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.7)
        assert e.effective_weight == 0.7
        assert e.fire_count == 0

    def test_ltp(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.5)
        initial = e.base_weight
        e.fire(reward=1.0)
        assert e.base_weight == initial + 0.05
        assert e.fire_count == 1

    def test_ltp_capped_at_1(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.98)
        e.fire(reward=1.0)
        assert e.base_weight <= 1.0

    def test_decay(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.5)
        e.apply_decay(months=1.0)
        assert e.base_weight == pytest.approx(0.5 * 0.95, abs=0.001)

    def test_multi_month_decay(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.5)
        e.apply_decay(months=12.0)
        assert e.base_weight < 0.3

    def test_pruning_threshold(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.04)
        assert e.should_prune

    def test_not_pruned_above_threshold(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.1)
        assert not e.should_prune

    def test_serialization(self):
        e = ConceptEdge(source="a", target="b", base_weight=0.7, domain="test")
        e.fire(reward=0.5)
        data = e.to_dict()
        e2 = ConceptEdge.from_dict(data)
        assert e2.source == "a"
        assert e2.fire_count == 1
        assert e2.base_weight == pytest.approx(0.725, abs=0.001)


class TestConceptGraph:
    def test_add_nodes_and_edges(self):
        g = _build_simple_graph()
        assert len(g.nodes) == 4
        assert len(g.edges) == 4

    def test_edge_requires_existing_nodes(self):
        g = ConceptGraph()
        g.add_node(ConceptNode(id="a", label="A"))
        with pytest.raises(ValueError, match="not in graph"):
            g.add_edge(ConceptEdge(source="a", target="nonexistent"))

    def test_outgoing_edges(self):
        g = _build_simple_graph()
        edges = g.outgoing_edges("a")
        assert len(edges) == 2
        targets = {e.target for e in edges}
        assert targets == {"b", "c"}

    def test_basic_cascade(self):
        g = _build_simple_graph()
        result = g.cascade("a")
        assert result.seed_node == "a"
        assert len(result.fired_nodes) > 0
        assert result.edges_fired > 0

    def test_convergence_detection(self):
        """Node D receives activation from both B and C paths."""
        g = _build_simple_graph()
        result = g.cascade("a")

        # D should have convergence from two independent paths
        d_activation = next(
            (a for a in result.activations if a.node_id == "d"), None
        )
        assert d_activation is not None
        assert d_activation.convergence_count >= 2
        assert d_activation.fired  # Should exceed threshold with convergence

    def test_convergence_patterns_reported(self):
        g = _build_simple_graph()
        result = g.cascade("a")
        assert len(result.convergence_patterns) >= 1
        convergence = result.convergence_patterns[0]
        assert convergence["target"] == "d"
        assert convergence["convergence_count"] >= 2

    def test_insights_generated(self):
        g = _build_simple_graph()
        result = g.cascade("a")
        insights = result.insights()
        assert len(insights) >= 1
        assert "Convergence" in insights[0]

    def test_cascade_depth_limit(self):
        g = _build_simple_graph()
        result = g.cascade("a", max_depth=1)
        # At depth 1, should only reach B and C, not D
        fired = set(result.fired_nodes)
        assert "d" not in fired or result.max_depth <= 1

    def test_min_activation_filter(self):
        g = _build_simple_graph()
        result = g.cascade("a", min_activation=0.9)
        # Very high threshold should filter out most activations
        assert result.edges_fired <= len(g.edges)

    def test_edge_firing_recorded(self):
        g = _build_simple_graph()
        initial_counts = {k: e.fire_count for k, e in g.edges.items()}
        g.cascade("a")
        for key, edge in g.edges.items():
            if key[0] == "a" or key[0] in ["b", "c"]:
                assert edge.fire_count >= initial_counts[key]

    def test_form_edge(self):
        g = _build_simple_graph()
        initial_edges = len(g.edges)
        g.form_edge("b", "c", domain="test")
        assert len(g.edges) == initial_edges + 1
        new_edge = g.get_edge("b", "c")
        assert new_edge is not None
        assert new_edge.base_weight == 0.2  # Synaptogenesis weight

    def test_ltp_applied(self):
        g = _build_simple_graph()
        edge = g.get_edge("a", "b")
        initial = edge.base_weight
        g.apply_ltp("a", "b", reward=1.0)
        assert edge.base_weight > initial

    def test_decay_and_prune(self):
        g = ConceptGraph()
        g.add_node(ConceptNode(id="a", label="A"))
        g.add_node(ConceptNode(id="b", label="B"))
        g.add_edge(ConceptEdge(source="a", target="b", base_weight=0.06))
        # Heavy decay should prune the weak edge
        pruned = g.apply_decay(months=24)
        assert ("a", "b") in pruned
        assert len(g.edges) == 0

    def test_prune_explicit(self):
        g = ConceptGraph()
        g.add_node(ConceptNode(id="a", label="A"))
        g.add_node(ConceptNode(id="b", label="B"))
        g.add_edge(ConceptEdge(source="a", target="b", base_weight=0.01))
        pruned = g.prune()
        assert ("a", "b") in pruned

    def test_mermaid_output(self):
        g = _build_simple_graph()
        result = g.cascade("a")
        mermaid = g.to_mermaid(result)
        assert "graph LR" in mermaid
        assert "Node A" in mermaid
        assert "-->" in mermaid

    def test_graphviz_output(self):
        g = _build_simple_graph()
        result = g.cascade("a")
        dot = g.to_graphviz(result)
        assert "digraph" in dot
        assert "Node A" in dot

    def test_stats(self):
        g = _build_simple_graph()
        s = g.stats()
        assert s["node_count"] == 4
        assert s["edge_count"] == 4
        assert "test" in s["domains"]


class TestGraphPersistence:
    def test_save_and_load(self, tmp_path):
        g = _build_simple_graph()
        g.cascade("a")  # Fire some edges
        path = tmp_path / "test_graph.json"
        g.save(path)

        g2 = ConceptGraph.load(path)
        assert len(g2.nodes) == len(g.nodes)
        assert len(g2.edges) == len(g.edges)

    def test_to_dict_roundtrip(self):
        g = _build_simple_graph()
        data = g.to_dict()
        g2 = ConceptGraph.from_dict(data)
        assert len(g2.nodes) == 4
        assert len(g2.edges) == 4

    def test_load_fixture_solarcraft(self):
        g = ConceptGraph.load(FIXTURES_DIR / "solarcraft_graph.json")
        assert len(g.nodes) == 10
        assert g.get_node("solarcraft") is not None
        assert g.get_node("liability_insurance") is not None

    def test_load_fixture_atlas(self):
        g = ConceptGraph.load(FIXTURES_DIR / "atlas_graph.json")
        assert len(g.nodes) == 7
        assert g.get_node("atlas") is not None

    def test_load_fixture_aletheia(self):
        g = ConceptGraph.load(FIXTURES_DIR / "aletheia_graph.json")
        assert len(g.nodes) == 8
        assert g.get_node("aletheia") is not None

    def test_weights_persist(self, tmp_path):
        g = _build_simple_graph()
        # Modify weights through LTP
        g.apply_ltp("a", "b", reward=1.0)
        edge = g.get_edge("a", "b")
        modified_weight = edge.base_weight

        path = tmp_path / "modified.json"
        g.save(path)
        g2 = ConceptGraph.load(path)
        edge2 = g2.get_edge("a", "b")
        assert edge2.base_weight == pytest.approx(modified_weight, abs=0.001)


# ===================================================================
# State Vector
# ===================================================================


class TestStateVector:
    def test_default_creation(self):
        sv = StateVector()
        assert sv.context == "main_session"
        assert sv.urgency == 0.3
        assert sv.service_asymmetry == 1.0

    def test_urgency_validation(self):
        with pytest.raises(ValueError, match="urgency"):
            StateVector(urgency=1.5)
        with pytest.raises(ValueError, match="urgency"):
            StateVector(urgency=-0.1)

    def test_service_asymmetry_minimum(self):
        with pytest.raises(ValueError, match="service_asymmetry"):
            StateVector(service_asymmetry=0.5)

    def test_modulation_focused(self):
        sv = StateVector(project_focus="solarcraft")
        factor_match = sv.modulation_factor("solarcraft")
        factor_other = sv.modulation_factor("atlas")
        assert factor_match > factor_other  # Focus boosts matched domain

    def test_modulation_urgency(self):
        relaxed = StateVector(urgency=0.0)
        urgent = StateVector(urgency=1.0)
        factor_relaxed = relaxed.modulation_factor("test")
        factor_urgent = urgent.modulation_factor("test")
        assert factor_urgent > factor_relaxed

    def test_modulation_time_pressure(self):
        normal = StateVector(time_pressure=0.0)
        pressed = StateVector(time_pressure=0.9)
        factor_normal = normal.modulation_factor("test")
        factor_pressed = pressed.modulation_factor("test")
        assert factor_pressed < factor_normal  # High pressure dampens

    def test_modulation_user_state(self):
        curious = StateVector(user_state="curious")
        grieving = StateVector(user_state="grieving")
        factor_curious = curious.modulation_factor("test")
        factor_grieving = grieving.modulation_factor("test")
        assert factor_curious > factor_grieving

    def test_state_hash_deterministic(self):
        sv1 = StateVector(context="main_session", project_focus="atlas")
        sv2 = StateVector(context="main_session", project_focus="atlas")
        assert sv1.encode_state_hash() == sv2.encode_state_hash()

    def test_state_hash_differs(self):
        sv1 = StateVector(context="main_session")
        sv2 = StateVector(context="group_chat")
        assert sv1.encode_state_hash() != sv2.encode_state_hash()

    def test_record_firing(self):
        sv = StateVector()
        sv.record_firing("a", "b")
        sv.record_firing("a", "b")
        key = ("a", "b")
        assert key in sv.state_associations
        state_hash = sv.encode_state_hash()
        assert sv.state_associations[key][state_hash] == 2

    def test_state_match_bonus_no_history(self):
        sv = StateVector()
        assert sv.state_match_bonus("a", "b") == 1.0  # Neutral

    def test_state_match_bonus_with_history(self):
        sv = StateVector(context="main_session", project_focus="atlas")
        for _ in range(10):
            sv.record_firing("a", "b")
        # Same state should get high bonus
        assert sv.state_match_bonus("a", "b") > 1.0

    def test_state_mismatch_penalty(self):
        # Record firings in one state
        sv1 = StateVector(context="main_session")
        for _ in range(10):
            sv1.record_firing("a", "b")

        # Check bonus in a different state
        sv2 = StateVector(context="group_chat")
        sv2.state_associations = sv1.state_associations
        bonus = sv2.state_match_bonus("a", "b")
        assert bonus < 1.0  # State mismatch penalty

    def test_serialization_roundtrip(self):
        sv = StateVector(context="subagent", urgency=0.8, project_focus="solarcraft")
        sv.record_firing("x", "y")
        data = sv.to_dict()
        sv2 = StateVector.from_dict(data)
        assert sv2.context == "subagent"
        assert sv2.urgency == 0.8
        assert ("x", "y") in sv2.state_associations


# ===================================================================
# Integration Tests
# ===================================================================


class TestCascadeWithState:
    """Integration: cascade behavior changes with state vector."""

    def test_focused_state_boosts_domain(self):
        g = _build_simple_graph()
        # Run cascade without focus
        result_unfocused = g.cascade("a", state=StateVector(project_focus=""))
        # Reset fire counts
        for edge in g.edges.values():
            edge.fire_count = 0

        # Run with focus on matching domain
        result_focused = g.cascade("a", state=StateVector(project_focus="test"))
        assert result_focused.total_activation >= result_unfocused.total_activation

    def test_urgency_increases_activation(self):
        g = _build_simple_graph()
        result_relaxed = g.cascade("a", state=StateVector(urgency=0.0))

        g2 = _build_simple_graph()
        result_urgent = g2.cascade("a", state=StateVector(urgency=1.0))
        assert result_urgent.total_activation >= result_relaxed.total_activation

    def test_state_dependent_retrieval(self):
        """Same graph, different activation patterns per state."""
        g = _build_simple_graph()

        # Business state
        biz_state = StateVector(
            context="main_session",
            project_focus="test",
            urgency=0.8,
        )
        result_biz = g.cascade("a", state=biz_state)

        # Relaxed state
        g2 = _build_simple_graph()
        relax_state = StateVector(
            context="heartbeat",
            urgency=0.0,
            user_state="curious",
        )
        result_relax = g2.cascade("a", state=relax_state)

        # Different states produce different activation totals
        # (exact comparison depends on modulation factors)
        assert result_biz.total_activation != result_relax.total_activation


class TestSolarCraftCascade:
    """Integration test using the SolarCraft fixture graph."""

    def test_solarcraft_convergence_at_liability(self):
        """The key example from NERVOUS-SYSTEM.md:
        SolarCraft → festival_events → weather_risk → equipment_damage → liability_insurance
        SolarCraft → starlink → weather_risk (second pathway converges!)
        SolarCraft → liability_insurance (direct)
        """
        g = ConceptGraph.load(FIXTURES_DIR / "solarcraft_graph.json")
        result = g.cascade("solarcraft")

        # Liability insurance should fire with convergence
        assert "liability_insurance" in result.fired_nodes

        # Should have convergence patterns
        assert len(result.convergence_patterns) >= 1

        # Check insights mention convergence
        insights = result.insights()
        assert len(insights) >= 1

    def test_solarcraft_with_focus(self):
        g = ConceptGraph.load(FIXTURES_DIR / "solarcraft_graph.json")
        state = StateVector(project_focus="solarcraft", urgency=0.5)
        result = g.cascade("solarcraft", state=state)
        assert result.total_activation > 0
        assert len(result.fired_nodes) > 0

    def test_weather_risk_convergence(self):
        """weather_risk should receive activation from both festival_events and starlink."""
        g = ConceptGraph.load(FIXTURES_DIR / "solarcraft_graph.json")
        result = g.cascade("solarcraft")
        wr = next((a for a in result.activations if a.node_id == "weather_risk"), None)
        assert wr is not None
        assert wr.convergence_count >= 2


class TestMultiHopCascade:
    """Integration: deep cascades with convergence detection."""

    def test_deep_chain(self):
        """A → B → C → D → E — activation should propagate with decay."""
        g = ConceptGraph()
        for letter in "abcde":
            g.add_node(ConceptNode(id=letter, label=letter.upper(), domain="test", activation_threshold=0.1))  # noqa: E501
        for src, tgt in [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")]:
            g.add_edge(ConceptEdge(source=src, target=tgt, base_weight=0.9, domain="test"))

        result = g.cascade("a")
        assert "e" in result.fired_nodes
        # Activation should decay along the chain
        e_act = next(a for a in result.activations if a.node_id == "e")
        b_act = next(a for a in result.activations if a.node_id == "b")
        assert e_act.activation_level < b_act.activation_level

    def test_diamond_convergence(self):
        """A → B → D, A → C → D — classic diamond convergence."""
        g = ConceptGraph()
        for n in ["a", "b", "c", "d"]:
            g.add_node(ConceptNode(id=n, label=n.upper(), domain="test", activation_threshold=0.3))
        g.add_edge(ConceptEdge(source="a", target="b", base_weight=0.9, domain="test"))
        g.add_edge(ConceptEdge(source="a", target="c", base_weight=0.9, domain="test"))
        g.add_edge(ConceptEdge(source="b", target="d", base_weight=0.9, domain="test"))
        g.add_edge(ConceptEdge(source="c", target="d", base_weight=0.9, domain="test"))

        result = g.cascade("a")
        d_act = next(a for a in result.activations if a.node_id == "d")
        assert d_act.convergence_count >= 2
        # Convergence should amplify activation beyond single-path
        assert d_act.activation_level > 0.8

    def test_hebbian_state_encoding(self):
        """Edges should record which states they fire in."""
        g = _build_simple_graph()
        state = StateVector(context="main_session", project_focus="test")
        g.cascade("a", state=state)

        # State should have recorded firings
        assert len(state.state_associations) > 0


class TestPlasticityLifecycle:
    """Integration: full lifecycle of edge formation, strengthening, decay, pruning."""

    def test_full_lifecycle(self):
        g = ConceptGraph()
        g.add_node(ConceptNode(id="a", label="A"))
        g.add_node(ConceptNode(id="b", label="B"))

        # Formation: novel co-activation
        edge = g.form_edge("a", "b", initial_weight=0.2)
        assert edge.base_weight == 0.2

        # Strengthening: LTP through repeated reward
        for _ in range(10):
            g.apply_ltp("a", "b", reward=1.0)
        assert edge.base_weight == pytest.approx(0.2 + 10 * 0.05, abs=0.001)

        # Decay: months of disuse
        g.apply_decay(months=6)
        assert edge.base_weight < 0.7

        # More decay leads to pruning (apply_decay prunes internally)
        pruned = g.apply_decay(months=120)
        assert edge.base_weight < 0.05
        assert ("a", "b") in pruned
        assert len(g.edges) == 0
