"""Tests for time-dependent evacuation route planning and bottleneck evasion."""
import networkx as nx
import pytest
from src.routing.router import EvacuationRouter
from src.routing.safety import SafetyEvaluator
from src.scenarios.synthetic import SyntheticFloodScenario


@pytest.fixture
def evacuation_graph():
    """
    Constructs a dual-corridor test network:
      Direct low corridor: A -> B -> D -> S (500m)
      High-ground detour: A -> C -> E -> S (1500m)
    """
    G = nx.DiGraph()
    G.graph["profile_mode"] = "driving"
    G.graph["max_safe_depth"] = 0.20

    # Nodes with coordinates
    nodes = {
        "A": {"x": 80.220, "y": 13.010},
        "B": {"x": 80.230, "y": 13.010},
        "D": {"x": 80.240, "y": 13.010},
        "C": {"x": 80.220, "y": 13.000},
        "E": {"x": 80.240, "y": 13.000},
        "S": {"x": 80.250, "y": 13.005},
    }
    for n, data in nodes.items():
        G.add_node(n, **data)

    # Direct corridor: 500m total
    # Driving: 40 km/h = 11.11 m/s
    G.add_edge("A", "B", length=100.0, travel_time=9.0, highway="primary", name="Direct Approach")
    G.add_edge("B", "D", length=300.0, travel_time=27.0, highway="primary", name="Low Bridge")
    G.add_edge("D", "S", length=100.0, travel_time=9.0, highway="primary", name="Shelter Link")

    # High-ground detour: 1500m total
    # Driving: 35 km/h = 9.72 m/s
    G.add_edge("A", "C", length=300.0, travel_time=31.0, highway="secondary", name="Detour Approach")
    G.add_edge("C", "E", length=900.0, travel_time=93.0, highway="secondary", name="High Bridge")
    G.add_edge("E", "S", length=300.0, travel_time=31.0, highway="secondary", name="Detour Shelter Link")

    return G


@pytest.fixture
def walking_evacuation_graph(evacuation_graph):
    """Walking version with walking speeds (1.25 m/s) and walking depth limit (0.15m)."""
    G_walk = nx.DiGraph(evacuation_graph)
    G_walk.graph["profile_mode"] = "walking"
    G_walk.graph["max_safe_depth"] = 0.15

    speed_mps = 1.25
    for u, v in G_walk.edges():
        length = G_walk[u][v]["length"]
        G_walk[u][v]["travel_time"] = length / speed_mps

    return G_walk


def test_dry_baseline_shortest_route(evacuation_graph):
    scenario = SyntheticFloodScenario("Dry Baseline")
    evaluator = SafetyEvaluator(scenario)
    router = EvacuationRouter(evaluator)

    result = router.find_route(
        G=evacuation_graph,
        origin_node="A",
        destination_nodes=["S"],
        departure_time_seconds=0.0,
    )

    assert result.status == "SUCCESS"
    assert result.path_nodes == ["A", "B", "D", "S"]
    assert result.total_distance_meters == 500.0
    assert pytest.approx(result.total_time_seconds, abs=1.0) == 45.0


def test_static_flood_diverts_to_high_ground(evacuation_graph):
    scenario = SyntheticFloodScenario("Static Flooded Bridge")
    # Low Bridge (B->D) is severely flooded (0.75m)
    scenario.set_static_edge_depth("B", "D", 0.75)

    evaluator = SafetyEvaluator(scenario)
    router = EvacuationRouter(evaluator)

    result = router.find_route(
        G=evacuation_graph,
        origin_node="A",
        destination_nodes=["S"],
        departure_time_seconds=0.0,
    )

    assert result.status == "SUCCESS"
    # Should automatically divert along high ground: A -> C -> E -> S
    assert result.path_nodes == ["A", "C", "E", "S"]
    assert result.total_distance_meters == 1500.0
    assert pytest.approx(result.total_time_seconds, abs=1.0) == 155.0


def test_dynamic_flood_time_awareness_driver_vs_walker(evacuation_graph, walking_evacuation_graph):
    """
    Low Bridge (B->D) stays dry until t=120s, then floods to 0.45m at t=200s.
    - Driver (leaves t=0): arrives at B at t=9s, traverses B->D by t=36s (< 120s) -> crosses safely!
    - Walker (leaves t=0): arrives at B at t=80s, finishes B->D at t=320s -> floods during crossing!
      Planner must proactively send the walker via high ground C->E.
    """
    scenario = SyntheticFloodScenario("Dynamic Flood Wave")
    scenario.set_dynamic_edge_curve(
        u="B",
        v="D",
        start_time_seconds=120.0,
        peak_time_seconds=200.0,
        peak_depth_m=0.45,
        base_depth_m=0.0,
    )

    evaluator = SafetyEvaluator(scenario)
    router = EvacuationRouter(evaluator)

    # 1. Test Driver
    driver_result = router.find_route(
        G=evacuation_graph,
        origin_node="A",
        destination_nodes=["S"],
        departure_time_seconds=0.0,
    )
    assert driver_result.status == "SUCCESS"
    # Driver safely beat the flood wave
    assert driver_result.path_nodes == ["A", "B", "D", "S"]

    # 2. Test Walker
    walker_result = router.find_route(
        G=walking_evacuation_graph,
        origin_node="A",
        destination_nodes=["S"],
        departure_time_seconds=0.0,
    )
    assert walker_result.status == "SUCCESS"
    # Walker would have been caught in flood; planner routed via high ground
    assert walker_result.path_nodes == ["A", "C", "E", "S"]
    assert walker_result.total_distance_meters == 1500.0


def test_complete_inundation_reports_no_safe_route(evacuation_graph):
    scenario = SyntheticFloodScenario("Total Inundation")
    # Both corridors flooded
    scenario.set_static_edge_depth("B", "D", 0.60)
    scenario.set_static_edge_depth("C", "E", 0.60)

    evaluator = SafetyEvaluator(scenario)
    router = EvacuationRouter(evaluator)

    result = router.find_route(
        G=evacuation_graph,
        origin_node="A",
        destination_nodes=["S"],
        departure_time_seconds=0.0,
    )

    assert result.status == "NO_SAFE_ROUTE"
    assert result.destination_node is None
    assert len(result.path_nodes) == 0
    assert len(result.diagnostics) >= 2
    # Verify that diagnostics mention blocked segments
    assert any("impassable" in d for d in result.diagnostics)
